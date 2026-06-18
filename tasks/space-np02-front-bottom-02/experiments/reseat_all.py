import subprocess
import re
import os
import json

# Setup paths
T = "tasks/space-np02-front-bottom-02"

results = []

for n in range(1, 9):
    art_path = f"{T}/experiments/SRC-nb-s{n}/raw.png"
    if not os.path.exists(art_path):
        print(f"Skipping s{n} because {art_path} does not exist.")
        continue
    
    out_dir = f"{T}/experiments/RESEAT-srcfinal-nb-s{n}"
    os.makedirs(out_dir, exist_ok=True)
    out_png = f"{out_dir}/exact.png"
    
    # 1. Run exact_bevel_composite
    cmd_composite = [
        "python3", "scripts/exact_bevel_composite.py",
        "--art", art_path,
        "--svg", f"{T}/source/template.svg",
        "--out", out_png,
        "--bbox-mode", "blue-locked",
        "--rim-scale", "1.2"
    ]
    print(f"\n======================================")
    print(f"Running composite for s{n}...")
    res_comp = subprocess.run(cmd_composite, capture_output=True, text=True)
    if res_comp.returncode != 0:
        print(f"Composite failed for s{n}:\n{res_comp.stderr}")
        continue
    
    stdout = res_comp.stdout
    print(stdout)
    
    # Parse bbox
    # Look for --bbox <numbers>
    match = re.search(r'--bbox\s+([0-9.,-]+)', stdout)
    if not match:
        print(f"Could not find bbox in output for s{n}")
        continue
    bbox_str = match.group(1)
    print(f"Detected bbox for s{n}: {bbox_str}")
    
    # 2. Run geom_iou
    region_iou_json = f"{out_dir}/region_iou.json"
    region_overlay_png = f"{out_dir}/region_overlay.png"
    cmd_iou = [
        "python3", "scripts/geom_iou.py",
        out_png,
        "--svg", f"{T}/source/template.svg",
        "--bbox", bbox_str,
        "--json-out", region_iou_json,
        "--out-overlay", region_overlay_png
    ]
    print(f"Running geom_iou for s{n}...")
    res_iou = subprocess.run(cmd_iou, capture_output=True, text=True)
    if res_iou.returncode != 0:
        print(f"geom_iou failed for s{n}:\n{res_iou.stderr}")
    else:
        print(res_iou.stdout)
    
    # 3. Run svg_geometry_check
    whitecheck_json = f"{out_dir}/whitecheck.json"
    overlay_png = f"{out_dir}/overlay.png"
    cmd_check = [
        "python3", "scripts/svg_geometry_check.py",
        out_png,
        "--svg", f"{T}/source/template.svg",
        "--bbox", bbox_str,
        "--json-out", whitecheck_json,
        "--out-overlay", overlay_png
    ]
    print(f"Running svg_geometry_check for s{n}...")
    res_check = subprocess.run(cmd_check, capture_output=True, text=True)
    if res_check.returncode != 0:
        print(f"svg_geometry_check failed for s{n}:\n{res_check.stderr}")
    else:
        print(res_check.stdout)
        
    # Read metrics
    region_iou_val = None
    openings_iou = {}
    if os.path.exists(region_iou_json):
        with open(region_iou_json, "r") as f_in:
            data = json.load(f_in)
            region_iou_val = data.get("mean_region_iou")
            for h in data.get("openings", []):
                openings_iou[f"opening_{h['i']}_{h['kind']}"] = h["region_iou"]
            
    white_iou_val = None
    painted_frac_val = None
    outside_frac_val = None
    if os.path.exists(whitecheck_json):
        with open(whitecheck_json, "r") as f_in:
            data = json.load(f_in)
            white_iou_val = data.get("mean_iou")
            outside_frac_val = data.get("outside_frac")
            holes = data.get("holes", [])
            if holes:
                painted_frac_val = max(h["painted_frac"] for h in holes)
            
    results.append({
        "candidate": f"SRC-nb-s{n}",
        "bbox": bbox_str,
        "region_iou": region_iou_val,
        "openings_region_iou": openings_iou,
        "white_iou": white_iou_val,
        "max_painted_frac": painted_frac_val,
        "outside_frac": outside_frac_val,
    })

print("\n=== SUMMARY OF RESEAT RESULTS ===")
print(json.dumps(results, indent=2))
with open(f"{T}/experiments/reseat_summary.json", "w") as f_out:
    json.dump(results, f_out, indent=2)
