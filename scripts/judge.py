#!/usr/bin/env python3
"""judge.py — programmatic VLM verdict for image edits (automate the eyeball).

Uses OpenAI gpt-4o vision (OPENAI_API_KEY from .secrets/openai.env) to return a STRICT-JSON
verdict so a script/loop can gate accept/patch/restart without a human.

Modes:
  check (default): inspect ONE image (optionally vs a style --ref) and report
      {wellformed, leftover_text, text_found[], style_match, artifacts[], verdict, notes}
  pairwise: compare A (--image) vs B (--ref) on --criterion, run BOTH orders to kill
      position bias, return {winner: A|B|tie, consistent: bool} (GenArena finding: pairwise
      forced-choice >> pointwise for edit quality).

Usage:
  python3 scripts/judge.py --image crop.png --check-text --style-ref surroundings.png
  python3 scripts/judge.py --mode pairwise --image A.png --ref B.png --criterion "cleaner, better-formed yellow taxi in watercolor style"
"""
import argparse, base64, io, json, os, sys
from pathlib import Path
import requests
from PIL import Image

MODEL = "gpt-4o"


def load_key():
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k
    env = Path(__file__).resolve().parent.parent / ".secrets" / "openai.env"
    for line in env.read_text().splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no OPENAI_API_KEY")


def data_uri(path, maxside=1024):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    s = maxside / max(w, h)
    if s < 1:
        img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
    b = io.BytesIO(); img.save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def call(messages, key, max_tokens=700):
    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      json={"model": MODEL, "messages": messages, "max_tokens": max_tokens,
                            "temperature": 0, "response_format": {"type": "json_object"}}, timeout=120)
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:400]}", file=sys.stderr); raise SystemExit(1)
    return json.loads(r.json()["choices"][0]["message"]["content"])


def img_part(path):
    return {"type": "image_url", "image_url": {"url": data_uri(path)}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="check", choices=["check", "pairwise"])
    ap.add_argument("--image", required=True)
    ap.add_argument("--ref", help="style ref (check) or candidate B (pairwise)")
    ap.add_argument("--style-ref", help="alias for --ref in check mode")
    ap.add_argument("--criterion", default="overall quality and style match")
    ap.add_argument("--element", default="the main edited element", help="what to assess")
    a = ap.parse_args()
    key = load_key()
    ref = a.ref or a.style_ref

    if a.mode == "check":
        sys_p = ("You are a strict QA judge for children's-book watercolor+ink illustrations. "
                 "Inspect the image and return ONLY JSON with keys: "
                 "wellformed (bool: is the main subject cleanly drawn, correct anatomy/shape, complete, "
                 "no melting/distortion), wellformed_reason (str), "
                 "leftover_text (bool: any visible letters/words/numbers/signage on the subject?), "
                 "text_found (list of strings of any text you can read, [] if none), "
                 "style_match (number 0-1: how well the subject matches the surrounding/ref watercolor+ink style; "
                 "1=perfect), artifacts (list of any defects: seams, halos, pasted look, ghosting, smears), "
                 "verdict (\"PASS\" or \"FAIL\"), notes (str). Be literal about text — even faint letters count.")
        content = [{"type": "text", "text": f"Assess {a.element} in this image. Criterion: {a.criterion}."}]
        content.append(img_part(a.image))
        if ref:
            content.append({"type": "text", "text": "Second image is the STYLE REFERENCE (surrounding art) to match:"})
            content.append(img_part(ref))
        out = call([{"role": "system", "content": sys_p}, {"role": "user", "content": content}], key)
        print(json.dumps(out, indent=2))
        raise SystemExit(0 if out.get("verdict") == "PASS" else 2)

    # pairwise: run both orders
    if not ref:
        raise SystemExit("pairwise needs --ref (candidate B)")
    sys_p = ("You are a forced-choice judge. Two images are candidates. Pick which BETTER satisfies the "
             "criterion. Return ONLY JSON: {winner: \"first\"|\"second\", reason: str}. No ties.")
    def ask(p1, p2):
        content = [{"type": "text", "text": f"Criterion: {a.criterion}. Which is better?"},
                   {"type": "text", "text": "FIRST:"}, img_part(p1),
                   {"type": "text", "text": "SECOND:"}, img_part(p2)]
        return call([{"role": "system", "content": sys_p}, {"role": "user", "content": content}], key)
    r1 = ask(a.image, ref)      # A first
    r2 = ask(ref, a.image)      # B first (swap)
    a_wins = (r1.get("winner") == "first") + (r2.get("winner") == "second")
    b_wins = (r1.get("winner") == "second") + (r2.get("winner") == "first")
    winner = "A" if a_wins > b_wins else ("B" if b_wins > a_wins else "tie")
    consistent = (a_wins == 2 or b_wins == 2)
    print(json.dumps({"winner": winner, "consistent": consistent,
                      "order1": r1, "order2": r2}, indent=2))
    raise SystemExit(0)


if __name__ == "__main__":
    main()
