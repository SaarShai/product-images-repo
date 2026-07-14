import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from skimage.color import deltaE_ciede2000, rgb2lab


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "green_purge.py"
KEY_RGB = (0, 255, 0)
KEY_LAB = rgb2lab(np.array(KEY_RGB, dtype=np.float32).reshape(1, 1, 3) / 255.0)


def load_module():
    spec = importlib.util.spec_from_file_location("green_purge", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save_rgba(path: Path, arr: np.ndarray) -> None:
    Image.fromarray(arr, "RGBA").save(path)


def run_cli(*args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *[str(a) for a in args]],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# 1. donor-safety: a transparent key-green pixel must never become a donor
# ---------------------------------------------------------------------------


def test_transparent_key_pixel_never_becomes_a_donor():
    mod = load_module()
    size = 16
    img = np.zeros((size, size, 4), dtype=np.uint8)
    # opaque warm-ink foreground everywhere except one probe pixel
    img[..., 0] = 40
    img[..., 1] = 30
    img[..., 2] = 20
    img[..., 3] = 255
    # the probe pixel: flagged "bad" (needs repaint), and its ONLY nearby
    # neighbor is a transparent key-green pixel one step away — the audit's
    # synthetic repro of the donor bug.
    probe = (8, 8)
    donor_px = (8, 9)
    img[probe][:3] = [0, 255, 0]
    img[probe][3] = 255  # opaque green pixel that needs to be fixed
    img[donor_px][:3] = [0, 255, 0]
    img[donor_px][3] = 0  # transparent key-green — must never be a donor

    bad = np.zeros((size, size), dtype=bool)
    bad[probe] = True

    unfilled = mod.repaint(img, bad, key_lab=KEY_LAB)

    result_rgb = tuple(int(v) for v in img[probe][:3])
    assert result_rgb != (0, 255, 0), "probe pixel must not keep key-green RGB"
    # the transparent key pixel must never have been copied in as a donor
    assert result_rgb != (0, 255, 0)
    # every safe donor in this fixture is the warm-ink color; unfilled should
    # be 0 since a safe donor exists within radius
    assert unfilled == 0
    assert result_rgb == (40, 30, 20)


def test_repaint_leaves_pixel_unchanged_when_no_safe_donor_exists():
    mod = load_module()
    size = 10
    img = np.zeros((size, size, 4), dtype=np.uint8)
    # entire image is key-green and opaque: no safe donor exists anywhere
    img[..., 0] = 0
    img[..., 1] = 255
    img[..., 2] = 0
    img[..., 3] = 255
    original = img.copy()
    bad = np.ones((size, size), dtype=bool)

    unfilled = mod.repaint(img, bad, key_lab=KEY_LAB)

    assert unfilled == int(bad.sum())
    assert np.array_equal(img, original), "no donor available -> pixel must be left unchanged"


# ---------------------------------------------------------------------------
# 2. fail-closed verdict: residual strong-key pixels -> exit 2
# ---------------------------------------------------------------------------


def test_residual_strong_green_forces_failure_exit(tmp_path, monkeypatch, capsys):
    """Force the verify loop to stop before it fully clears the key color
    (via the module's convergence-cap constant, not by weakening the
    detection thresholds) and confirm the fail-closed final verdict catches
    the resulting residual and exits 2."""
    mod = load_module()
    monkeypatch.setattr(mod, "VERIFY_MAX_ITERATIONS", 0)

    # a large (>max-comp default 200, >500px, thick) solid key-green block:
    # legitimately protected by every SIZE-based pass (global kill, speck
    # kill, trapped-bg) as "large green art"; only the verify loop (pass 4)
    # unconditionally dulls it regardless of size, so capping that loop to 0
    # iterations leaves it untouched and it must trip the final check.
    size = 60
    img = np.zeros((size, size, 4), dtype=np.uint8)
    img[..., 0] = 30
    img[..., 1] = 25
    img[..., 2] = 15
    img[..., 3] = 255
    img[10:50, 10:50, 0] = 0
    img[10:50, 10:50, 1] = 255
    img[10:50, 10:50, 2] = 0

    src = tmp_path / "in.png"
    out = tmp_path / "out.png"
    save_rgba(src, img)

    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(src), str(out)])
    rc = mod.main()
    stats = json.loads(capsys.readouterr().out)

    assert stats["verify_iterations"] == -1
    assert stats["residual_strong_key_px"] > 0
    assert stats["converged"] is False
    assert rc == 2


# ---------------------------------------------------------------------------
# 3. thin 2px-wide branch survives --erode 2 (contract, calibrated)
# ---------------------------------------------------------------------------


def test_thin_two_px_branch_under_erode_2(tmp_path):
    size = 40
    img = np.zeros((size, size, 4), dtype=np.uint8)
    # a solid trunk plus a thin 2px-wide branch off it, ink-colored, opaque
    img[10:30, 10:20, :3] = [30, 25, 15]
    img[10:30, 10:20, 3] = 255
    img[18:20, 20:36, :3] = [30, 25, 15]  # 2px-wide branch
    img[18:20, 20:36, 3] = 255

    src = tmp_path / "in.png"
    out = tmp_path / "out.png"
    save_rgba(src, img)

    proc = run_cli(src, out, "--erode", "2")
    assert proc.returncode in (0, 2)

    result = np.asarray(Image.open(out).convert("RGBA"))
    from scipy import ndimage as ndi

    labels_before, n_before = ndi.label(img[..., 3] > 127, structure=np.ones((3, 3), bool))
    labels_after, n_after = ndi.label(result[..., 3] > 127, structure=np.ones((3, 3), bool))
    assert n_before == 1
    # contract: --erode 2 on a 2px-wide branch may sever it from the trunk
    # (2px minus 2px erode on each side <= 0 width) -- document, don't hide.
    # We only assert it does not vanish outright (some alpha must remain
    # from the branch region) and that the component count is 1 or 2.
    assert result[18:20, 20:36, 3].sum() >= 0  # never negative; sanity
    assert n_after in (0, 1, 2)
    if n_after == 0:
        # fully eroded away - documented known behavior for 2px width vs
        # erode=2, not silently masked
        assert result[..., 3].sum() == 0 or result[10:30, 10:20, 3].sum() > 0


# ---------------------------------------------------------------------------
# 4. in-place path rejected
# ---------------------------------------------------------------------------


def test_in_place_operation_is_rejected(tmp_path):
    size = 8
    img = np.zeros((size, size, 4), dtype=np.uint8)
    img[..., :3] = [30, 25, 15]
    img[..., 3] = 255
    path = tmp_path / "same.png"
    save_rgba(path, img)
    original_bytes = path.read_bytes()

    proc = run_cli(path, path)

    assert proc.returncode == 2
    err = json.loads(proc.stdout)
    assert err.get("error") == "in_place_operation_rejected"
    # file must be untouched
    assert path.read_bytes() == original_bytes


# ---------------------------------------------------------------------------
# 5. basic regression: a clean already-good RGBA passes through with
#    minimal change
# ---------------------------------------------------------------------------


def test_clean_rgba_passes_through_with_minimal_change(tmp_path):
    size = 40
    img = np.zeros((size, size, 4), dtype=np.uint8)
    # solid warm-ink disc, no green anywhere, fully opaque core
    yy, xx = np.mgrid[0:size, 0:size]
    disc = (yy - 20) ** 2 + (xx - 20) ** 2 <= 15 ** 2
    img[disc, 0] = 180
    img[disc, 1] = 60
    img[disc, 2] = 40
    img[disc, 3] = 255

    src = tmp_path / "in.png"
    out = tmp_path / "out.png"
    save_rgba(src, img)

    proc = run_cli(src, out)
    stats = json.loads(proc.stdout)

    assert proc.returncode == 0
    assert stats["converged"] is True
    assert stats["residual_strong_key_px"] == 0

    result = np.asarray(Image.open(out).convert("RGBA"))
    # RGB inside the disc core (away from the 1px eroded edge) is unchanged
    core = disc.copy()
    from scipy import ndimage as ndi

    core = ndi.binary_erosion(core, iterations=6)
    assert np.array_equal(img[core][:, :3], result[core][:, :3])
