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


def test_repaint_never_self_donates_a_bad_pixel_that_would_pass_the_hardcoded_safe_thresholds():
    """Round-7/round-8 audit repro: DONOR_DOMINANCE_MAX=18 and a bad pixel of
    dominance=15 independently satisfies repaint()'s own safe-donor
    predicate (opaque, dominance<=18, deltaE>=10 to key). Pre-fix, `safe`
    never excluded `bad`, so this pixel's own array location counted as its
    own nearest safe donor at distance 0 -- it "donated" to itself, stayed
    (100,115,100) unchanged, and was counted as filled (unfilled=0). A real,
    differently-colored safe donor surrounds it here; post-fix the probe
    pixel must actually take on the real donor's RGB, not keep its own."""
    mod = load_module()
    size = 16
    img = np.zeros((size, size, 4), dtype=np.uint8)
    img[..., 0] = 40
    img[..., 1] = 30
    img[..., 2] = 20
    img[..., 3] = 255
    probe = (8, 8)
    img[probe][:3] = [100, 115, 100]  # dominance = 115 - 100 = 15 (<= 18)
    img[probe][3] = 255

    bad = np.zeros((size, size), dtype=bool)
    bad[probe] = True

    unfilled = mod.repaint(img, bad, key_lab=KEY_LAB)

    result_rgb = tuple(int(v) for v in img[probe][:3])
    assert unfilled == 0, "a genuine safe donor exists nearby; must be counted as filled"
    assert result_rgb != (100, 115, 100), "probe must not keep its own RGB via self-donation"
    assert result_rgb == (40, 30, 20), "probe must take the real surrounding donor's RGB"


def test_no_self_donation_and_unfilled_counted_at_nondefault_dominance_and_tau_flags(tmp_path):
    """(brief item 9, exact repro condition) A uniform dominance=15 image has
    NO genuine safe donor anywhere -- every candidate donor pixel is itself
    equally "bad". With default --dominance 18 (== DONOR_DOMINANCE_MAX) this
    dominance=15 fixture would never even be flagged bad by the CLI's band
    pass; --dominance 10 (non-default, looser than the hardcoded donor
    threshold) is what actually exercises the coincidence-closed hole, along
    with a non-default --tau 20. Pre-fix, self-donation would leave the
    pixels unchanged while wrongly reporting band_green_unfilled_px == 0.
    Post-fix, since no real donor exists, they must be correctly reported
    unfilled (not silently "fixed") and the pixels must be left untouched
    (never an invented RGB), which now also fails the run via the item-10
    fail-closed fix."""
    size = 20
    img = np.zeros((size, size, 4), dtype=np.uint8)
    img[..., 0] = 100
    img[..., 1] = 115
    img[..., 2] = 100
    img[..., 3] = 255

    src = tmp_path / "in.png"
    out = tmp_path / "out.png"
    save_rgba(src, img)

    # --band 100 on a 20x20 image erodes the "inner" region to nothing, so
    # the entire foreground counts as "band" -- there is no non-band pixel
    # left over to serve as a real donor either.
    proc = run_cli(src, out, "--dominance", "10", "--tau", "20", "--band", "100")
    stats = json.loads(proc.stdout)

    assert stats["band_green_px"] > 0
    assert stats["band_green_unfilled_px"] == stats["band_green_px"], (
        "no genuine safe donor exists anywhere in this uniform fixture; "
        "self-donation would wrongly report these as filled (unfilled=0)"
    )
    assert stats["total_unfilled_px"] > 0
    assert stats["residual_strong_key_px"] == 0, "D3b alone does not see this class of leftover"
    assert stats["converged"] is False
    assert proc.returncode == 2

    result = np.asarray(Image.open(out).convert("RGBA"))
    # never invented: with no real donor, RGB must be left exactly as-is
    assert np.array_equal(result[..., :3], img[..., :3])


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


def test_any_nonzero_unfilled_counter_alone_forces_non_convergence(tmp_path, monkeypatch, capsys):
    """(brief item 10) The fail-closed verdict must react to EVERY repaint()
    unfilled counter (band_green/olive_notch/global_kill/speck_kill), not
    just the separate D3b residual re-measurement -- those counters record
    pixels repaint() explicitly could NOT fix, which is a different (and, on
    a dominance-15 fixture like this, non-overlapping) failure class than a
    literal deltaE<6 residual. Force every repaint() call to report 5 px
    unfilled (isolated from the donor-exclusion fix under test elsewhere in
    this file) and confirm converged flips to False / exit 2 even though the
    D3b residual check and both convergence loops are clean on this
    non-green fixture."""
    mod = load_module()

    def fake_repaint(img, bad, key_lab=None, search_radius=mod.DONOR_SEARCH_RADIUS):
        return 5

    monkeypatch.setattr(mod, "repaint", fake_repaint)

    size = 30
    img = np.zeros((size, size, 4), dtype=np.uint8)
    img[..., :3] = [180, 60, 40]  # solid warm ink, nowhere near key green
    img[..., 3] = 255
    src = tmp_path / "in.png"
    out = tmp_path / "out.png"
    save_rgba(src, img)

    monkeypatch.setattr(sys, "argv", [str(SCRIPT), str(src), str(out), "--no-green-art"])
    rc = mod.main()
    stats = json.loads(capsys.readouterr().out)

    assert stats["total_unfilled_px"] > 0
    assert stats["residual_strong_key_px"] == 0, "this fixture has no real key-adjacent pixels"
    assert stats["verify_converged"] is True
    assert stats["final_sweep_converged"] is True
    assert stats["converged"] is False
    assert rc == 2


# ---------------------------------------------------------------------------
# 3. thin 2px-wide branch is fully eroded by --erode 2, trunk survives
#    (contract, calibrated against MEASURED behavior, not assumed)
# ---------------------------------------------------------------------------


def test_thin_two_px_branch_is_fully_eroded_by_erode_2_trunk_survives(tmp_path):
    """Measured (not assumed) behavior: a 2px-wide branch is narrower than
    2x the erode radius, so --erode 2 erases it completely (every pixel in
    its region drops to alpha 0); only the solid trunk survives, as a single
    connected component. This replaces a prior version of this test whose
    name claimed the branch "survives" while its assertions (`sum() >= 0`,
    `n_after in (0, 1, 2)`) could not fail regardless of what the script
    did -- including if the branch-erosion behavior were silently deleted.
    If this measured contract ever changes, re-measure and re-assert; do not
    loosen these assertions to make a code regression pass."""
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
    assert proc.returncode == 0

    result = np.asarray(Image.open(out).convert("RGBA"))
    from scipy import ndimage as ndi

    labels_before, n_before = ndi.label(img[..., 3] > 127, structure=np.ones((3, 3), bool))
    labels_after, n_after = ndi.label(result[..., 3] > 127, structure=np.ones((3, 3), bool))
    assert n_before == 1

    # the branch is fully severed: every pixel in its region is now fully
    # transparent (a real measurement, not a "never negative" sanity no-op)
    assert result[18:20, 20:36, 3].sum() == 0

    # the trunk survives with the bulk of its area intact -- the 2px rim
    # erosion trims its border but the branch's disappearance is the only
    # thing that can sever it into a separate component
    trunk_before = int(img[10:30, 10:20, 3].sum())
    trunk_after = int(result[10:30, 10:20, 3].sum())
    assert trunk_after > trunk_before * 0.4, "trunk must survive erode 2, not just 'not go negative'"

    # exactly one component remains after the branch vanishes: the trunk
    assert n_after == 1


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
