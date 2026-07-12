#!/usr/bin/env python3
"""subgen.py — THE single, always-working way to generate images on the user's
SUBSCRIPTION (no API keys). Use this everywhere; do not drive codex/agy ad-hoc.

Providers (both already authenticated on this machine):
  openai : OpenAI gpt-image via `codex exec`
  nano   : Google Nano Banana via `agy`

Why this exists / what it fixes (every flaky failure mode we hit):
  * TIMEOUT ORPHANS — codex's node wrapper, on timeout, left the native binary
    running (reparented to PID 1) holding the output, so a retry spawned a 2nd
    concurrent codex. FIX: each call runs in its OWN process group
    (start_new_session) and on timeout we killpg the WHOLE group — no orphans.
  * PICKER RACES — mtime "newest image" discovery cross-assigned images across
    concurrent calls. FIX: deterministic per-call discovery — codex prints a
    per-call `session id:` on stderr (→ its exact output dir); agy prints the
    exact written path. Falls back to before/after set-diff, then newest.
  * NO-IMAGE — codex sometimes answers in text without rendering. FIX: a forceful
    "you MUST call the image tool" preamble + retry until a VALID image appears.
  * INVALID/EMPTY — FIX: every output is verified (PIL opens it, sane size).
  * AUTH/HEALTH — `--health` probes both providers before a run.

CLI:
  python3 scripts/subgen.py --health
  python3 scripts/subgen.py --provider openai --prompt-file P.md --out O.png -i a.png b.png
  python3 scripts/subgen.py --provider nano   --prompt "..."      --out O.png -i a.png
Library:
  from subgen import generate, health
  generate("openai", prompt, [imgs], out, timeout=300, retries=3) -> Path
"""
from __future__ import annotations
import argparse, glob, os, re, shutil, signal, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_images  # single source of truth for codex output-file discovery

AGY_BRAIN = Path.home() / ".gemini" / "antigravity-cli" / "brain"
_PATH_RE = re.compile(r"(/[^\s`'\"]+\.(?:jpg|jpeg|png))", re.I)
_SID_RE = re.compile(r"session id:\s*([0-9a-fA-F-]{36})")


def _valid_image(p) -> bool:
    try:
        from PIL import Image
        if not p or not os.path.exists(p) or os.path.getsize(p) < 8000:
            return False
        Image.open(p).verify()
        w, h = Image.open(p).size
        return w >= 64 and h >= 64
    except Exception:
        return False


_NANO_TALL_RATIO = 1.6  # h/w above this = "tall"; nano is square-biased and recomposes tall panels


def _warn_nano_tall(images):
    """NON-BREAKING: if any input/ref image is tall (h/w > ~1.6), warn to stderr that
    nano (Nano Banana) is square-biased and recomposes tall panels — prefer openai.
    Inspection only; never changes generation behavior or raises."""
    try:
        from PIL import Image
        for img in images:
            try:
                w, h = Image.open(img).size
            except Exception:
                continue
            if w and h / w > _NANO_TALL_RATIO:
                print(f"[subgen nano] WARNING: ref/target '{img}' is tall "
                      f"(h/w={h / w:.2f} > {_NANO_TALL_RATIO}). Nano Banana is square-biased "
                      f"and recomposes/crops tall panels — use --provider openai for tall panels.",
                      file=sys.stderr)
                return
    except Exception:
        pass


def _run(cmd, stdin_text, timeout):
    """Run cmd in its OWN process group; killpg the whole group on timeout.
    Returns (rc, stdout, stderr, timed_out)."""
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = p.communicate(input=stdin_text, timeout=timeout)
        return p.returncode, out, err, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:
            pass
        try:
            out, err = p.communicate(timeout=10)
        except Exception:
            out, err = "", ""
        return -1, out or "", err or "", True


def _discover_codex(stdout, stderr, before):
    # 1. exact: per-call session id -> its dir
    for txt in (stderr, stdout):
        m = _SID_RE.search(txt or "")
        if m:
            d = codex_images.CODEX_DIR / m.group(1)
            if d.is_dir():
                pngs = sorted(codex_images.session_images(d),
                              key=os.path.getmtime, reverse=True)
                if pngs:
                    return pngs[0]
    # 2. set-diff (one new file)
    after = set(codex_images.all_images())
    new = sorted(after - before, key=os.path.getmtime, reverse=True)
    if new:
        return new[0]
    return None


def gen_openai(prompt, images, out, timeout=300, retries=3, model=None) -> Path:
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    force = ("You MUST call your image-generation tool to actually RENDER exactly one image now. "
             "Do not only describe it; produce the image file.\n\n")
    base = ["codex", "exec", "--skip-git-repo-check"]
    if model:
        base += ["-m", model]
    for img in images:
        base += ["-i", str(img if Path(img).is_absolute() else Path.cwd() / img)]
    base += ["-"]
    for attempt in range(1, retries + 1):
        before = set(codex_images.all_images())
        rc, o, e, to = _run(base, force + prompt, timeout)
        cand = _discover_codex(o, e, before)
        if _valid_image(cand):
            shutil.copy(cand, out)
            print(f"[subgen openai] OK attempt {attempt} -> {out}", file=sys.stderr)
            return out
        print(f"[subgen openai] attempt {attempt}/{retries} no valid image (timeout={to})", file=sys.stderr)
    raise RuntimeError(f"openai gen failed after {retries} attempts -> {out}")


def gen_nano(prompt, images, out, timeout=300, retries=3) -> Path:
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    imgs = [str(Path(i).resolve()) for i in images]
    _warn_nano_tall(imgs)  # NON-BREAKING aspect advisory; does not change generation
    add = []
    for d in {str(Path(i).parent) for i in imgs} | {str(out.parent.resolve())}:
        add += ["--add-dir", d]
    full = (
        "You are an image-generation operator. Use ONLY your built-in generate_image tool "
        "(Nano Banana / Gemini image) to synthesize ONE high-resolution image. Do NOT write "
        "Python/Pillow/any code and do NOT just composite inputs — actually generate.\n\n"
        + prompt
        + ("\n\nPass these images to generate_image: " + ", ".join(imgs) if imgs else "")
        + "\n\nAfter generate_image returns, print the exact absolute source path it wrote.")
    cmd = ["agy", "--dangerously-skip-permissions", *add, "--print", full]
    for attempt in range(1, retries + 1):
        t0 = time.time() - 1
        rc, o, e, to = _run(cmd, None, timeout)
        cand = None
        for m in _PATH_RE.findall(o or ""):
            if os.path.exists(m) and os.path.getmtime(m) >= t0:
                cand = m
        if not cand:  # fallback: newest brain image written during this call
            files = [f for ext in ("jpg", "jpeg", "png")
                     for f in glob.glob(str(AGY_BRAIN / "*" / f"*.{ext}"))
                     if os.path.getmtime(f) >= t0]
            if files:
                cand = max(files, key=os.path.getmtime)
        if _valid_image(cand):
            shutil.copy(cand, out)
            print(f"[subgen nano] OK attempt {attempt} -> {out}", file=sys.stderr)
            return out
        print(f"[subgen nano] attempt {attempt}/{retries} no valid image (timeout={to})", file=sys.stderr)
    raise RuntimeError(f"nano gen failed after {retries} attempts -> {out}")


def generate(provider, prompt, images, out, timeout=300, retries=3, model=None) -> Path:
    if provider in ("openai", "codex", "gpt-image"):
        return gen_openai(prompt, images, out, timeout, retries, model)
    if provider in ("nano", "nanobanana", "agy", "gemini"):
        return gen_nano(prompt, images, out, timeout, retries)
    raise ValueError(f"unknown provider {provider}")


def health() -> dict:
    res = {}
    rc, o, e, to = _run(["codex", "exec", "--skip-git-repo-check", "-"],
                        "Reply with the single word OK and nothing else.", 90)
    res["openai"] = "ok" if (not to and "OK" in (o or "").upper()) else f"FAIL(timeout={to})"
    rc, o, e, to = _run(["agy", "--dangerously-skip-permissions", "--print",
                        "Reply with the single word OK and nothing else."], None, 60)
    res["nano"] = "ok" if (not to and "OK" in (o or "").upper()) else f"FAIL(timeout={to})"
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["openai", "nano"])
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("-i", "--image", nargs="*", default=[])
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--model")
    ap.add_argument("--health", action="store_true")
    a = ap.parse_args()
    if a.health:
        print(health()); return 0
    prompt = a.prompt or (a.prompt_file.read_text() if a.prompt_file else None)
    if not (a.provider and prompt and a.out):
        print("need --provider, --prompt/--prompt-file, --out", file=sys.stderr); return 2
    try:
        p = generate(a.provider, prompt, a.image, a.out, a.timeout, a.retries, a.model)
        print(p); return 0
    except Exception as ex:
        print(f"ERROR: {ex}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
