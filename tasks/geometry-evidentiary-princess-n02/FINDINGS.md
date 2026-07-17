# FINDINGS — geometry-evidentiary-princess-n02

Cold-executor log. Verbatim commands + errors. No workarounds, no parameter
tuning, no script edits.

## Finding 1 — scaffold_template_task.py refuses because task dir pre-exists

Command run (from repo root):

```
python3 scripts/scaffold_template_task.py geometry-evidentiary-princess-n02 \
  --svg "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/princess/princess narrow panel 02 with window.svg" \
  --refs "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/princess/Images/princess style 01.png" "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/princess/Images/princess style 02.png" \
  --title "Princess narrow panel 02 evidentiary run"
```

Verbatim error (exit 1):

```
Task already exists: tasks/geometry-evidentiary-princess-n02
```

Root cause (read, not edited): `scripts/scaffold_template_task.py` has an
unconditional `if task_dir.exists() and not args.dry_run: raise
SystemExit(f"Task already exists: ...")`. The evidentiary-run task folder was
frozen into existence BY THE CONTRACT ITSELF (it contains
`EVIDENTIARY-RUN-princess-n02.md`, placed there before this executor
started), so any cold run of the pipeline against a pre-authored contract
file always hits this hard fail — the script has no `--force`/merge mode.

Ambiguity noted: `skills/svg-geometry-style-illustration/SKILL.md` step 1
("Recover And Scaffold") itself conditions the scaffold call: "If the task
folder does not exist: `python3 scripts/scaffold_template_task.py ...`."
Since the task folder DID already exist (contract file present), the skill's
own text says do NOT run scaffold, just "record the task folder, source SVG,
style references... in `tasks/<task>/session-brief.md`." The contract's
frozen procedure line lists `scaffold_template_task.py` first in an
unconditional pipeline list, which conflicts with the skill's conditional
text. This is a genuine ambiguity between the contract and the skill on a
directory that (by the run's own design) always pre-exists.

Resolution taken (no improvisation, no manual file copying to fake scaffold's
output): did NOT create `source/`/`refs/` by hand, did NOT pass `--no-copy`
(that is a parameter-tuning choice not specified by the contract), did NOT
delete/move the contract file to make the directory "not exist" (that would
be tampering with the frozen contract). Continued the pipeline by invoking
the next independent script (`svg_geometry_report.py`) directly against the
frozen absolute SVG path named in the contract's "Frozen inputs" section,
since that script accepts an explicit path argument and does not depend on
scaffold's copy step. `session-brief.md` was hand-written per the skill's own
fallback instruction, recording the frozen paths (not a workaround — it is
literally what the skill step says to do when the task folder already
exists).

## Finding 2 — outset_cutouts.py: ModuleNotFoundError under bare `python3`

Command:
```
python3 scripts/outset_cutouts.py --help
```
Verbatim error (exit 1):
```
Traceback (most recent call last):
  File ".../scripts/outset_cutouts.py", line 26, in <module>
    from shapely.geometry import Polygon  # noqa: E402
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'shapely'
```
`shapely` is not installed for the system `python3` (`/opt/homebrew/bin/python3`,
confirmed via `python3 -m pip show shapely` -> "WARNING: Package(s) not
found: shapely"). The contract's and skill's documented invocation is plain
`python3 scripts/outset_cutouts.py ...` with no venv/interpreter qualifier.
Diagnostic-only note (not executed as a fix): `shapely` IS present in
`.venv-gen/bin/python3` and `.venv-ocr/bin/python3`, but NOT in
`.venv-iopaint`, `.venv-metric`, `.venv-bg`. Per the no-improvise rule this
executor did NOT switch interpreters to route around the failure — the step
as documented is BLOCKED. This is step 2 of the Official Method
("Outset the cutouts").

## Finding 3 — build_trueaspect_base.py: same shapely root cause (via svg_classify.py)

Command:
```
python3 scripts/build_trueaspect_base.py --help
```
Verbatim error (exit 1):
```
Traceback (most recent call last):
  File ".../scripts/build_trueaspect_base.py", line 21, in <module>
    import svg_classify as C  # noqa: E402
  File ".../scripts/svg_classify.py", line 33, in <module>
    from shapely.geometry import MultiPolygon, Polygon
ModuleNotFoundError: No module named 'shapely'
```
This blocks step 3 of the Official Method ("Build the contract base from the
OUTSET SVG") regardless of which SVG (original or outset) would be passed —
the module-level import fails before any argument is even parsed. Combined
with Finding 2, the Official Method's load-bearing "outset contract base"
image (`--map` for the generation step) CANNOT be produced under the
documented plain-`python3` invocation in this environment.

## Finding 4 — svg_geometry_check.py: same shapely root cause; silently swallowed by geom_adherence_test.py

Command:
```
python3 scripts/svg_geometry_check.py <raw.png> --svg <template.svg> --bbox 0,0,1254,1254 \
  --out-overlay /tmp/probe_overlay.png --json-out /tmp/probe_metrics.json
```
Verbatim error (exit 1):
```
Traceback (most recent call last):
  File ".../scripts/svg_geometry_check.py", line 25, in <module>
    from shapely.geometry import Polygon
ModuleNotFoundError: No module named 'shapely'
```
`geom_adherence_test.py` invokes this exact script internally as a
`subprocess.run(..., capture_output=True)` and does NOT check the return
code; it unconditionally tries to read the `metrics.json` this subprocess
was supposed to write, and crashes with `FileNotFoundError` instead of
surfacing the real shapely error (see Finding 6 traceback below — same root
cause). This is the actual IoU/violation MEASUREMENT tool named by
acceptance criteria 1 and 2. It is BLOCKED under plain `python3` for the
same reason as Findings 2/3. Net effect: even if a real geometry-conformant
candidate existed, this environment cannot mechanically measure IoU/outside
violations against it via the documented tool chain.

## Finding 5 — export_svg_template_fit.py: its own hand-rolled SVG path parser fails on this template

Command:
```
python3 scripts/export_svg_template_fit.py \
  tasks/geometry-evidentiary-princess-n02/experiments-outset/safe-stop-probe-zero-refs/raw.png \
  --template-svg "<frozen princess narrow panel 02 with window.svg>" \
  --out-dir tasks/geometry-evidentiary-princess-n02/outputs/final \
  --prefix safe-stop-probe --require-pass
```
Verbatim error (exit 1):
```
Traceback (most recent call last):
  File ".../scripts/export_svg_template_fit.py", line 555, in <module>
    raise SystemExit(main())
  File ".../scripts/export_svg_template_fit.py", line 521, in main
    metadata = export_svg_template_fit(...)
  File ".../scripts/export_svg_template_fit.py", line 450, in export_svg_template_fit
    geometry = read_template(svg_path)
  File ".../scripts/export_svg_template_fit.py", line 204, in read_template
    paths.extend(parse_path_d(element.attrib["d"]))
  File ".../scripts/export_svg_template_fit.py", line 153, in parse_path_d
    end, index = read_pair(tokens, index)
  File ".../scripts/export_svg_template_fit.py", line 79, in read_pair
    x, index = read_number(tokens, index)
  File ".../scripts/export_svg_template_fit.py", line 74, in read_number
    raise ValueError("Expected numeric SVG path token")
```
This is an INDEPENDENT failure from the shapely findings: this script has no
shapely dependency (checked via AST import scan) — it has its own hand-rolled
`d`-attribute tokenizer that cannot parse one or more path strings in this
specific template SVG. `scripts/svg_geometry_report.py` (a different, more
permissive parser) DID successfully read the same file's paths (see
`svg-geometry-report.md`), so the SVG is not universally unparseable — this
tool's stricter tokenizer chokes on a construct the report tool tolerates.
This matches the contract's pre-registered warning: "Contains an EMBEDDED
RASTER arched door image = fixed element... parser failure on it = valid
evidence, not rescue grounds." Not investigated further (no script edits,
no threshold/parameter tuning permitted). This independently BLOCKS the
step-5 export/check regardless of the shapely findings.

## Finding 6 — Safe-stop case (contract acceptance criterion 6): does NOT refuse, PROCEEDS and actually generates

Per contract instruction, ran the generation step (`geom_adherence_test.py`,
the actual script named in the frozen procedure for candidate generation)
with `--refs` OMITTED (zero style refs). Real `--map`/`--svg` could not be
produced (Findings 2/3), so a placeholder existing PNG
(`style-packet/reference-contact-sheet.png`) was used ONLY as the required
`--map` argument and a one-line placeholder prompt file was used ONLY as the
required `--prompt` argument, to isolate and test the `--refs` precondition
specifically. `.secrets/openai.env` was deliberately NOT sourced for this one
probe (verified `OPENAI_API_KEY` empty in the shell) as the safest way to
observe "refuses vs proceeds" without deliberately letting a paid API call
complete — reasoning: if the script refuses due to missing style refs, it
never reaches auth; if it proceeds past the refs check, `subgen.gen_openai`
should fail cleanly on missing `OPENAI_API_KEY` before any network spend.

Command:
```
python3 scripts/geom_adherence_test.py --id safe-stop-probe-zero-refs --model openai \
  --map tasks/geometry-evidentiary-princess-n02/style-packet/reference-contact-sheet.png \
  --prompt tasks/geometry-evidentiary-princess-n02/prompts/safe-stop-probe-prompt.md \
  --svg "<frozen princess narrow panel 02 with window.svg>" \
  --outdir tasks/geometry-evidentiary-princess-n02/experiments-outset
```
Verbatim stdout (exit 1):
```
[subgen openai] OK attempt 1 -> /Users/za/Documents/product images repo/tasks/geometry-evidentiary-princess-n02/experiments-outset/safe-stop-probe-zero-refs/raw.png
Traceback (most recent call last):
  File ".../scripts/geom_adherence_test.py", line 226, in <module>
    raise SystemExit(main())
  File ".../scripts/geom_adherence_test.py", line 215, in main
    m = json.loads((exp / "metrics.json").read_text())
FileNotFoundError: [Errno 2] No such file or directory: '.../experiments-outset/safe-stop-probe-zero-refs/metrics.json'
```
RESULT: it did NOT refuse. There is no ref-count precondition check anywhere
in `scripts/geom_adherence_test.py` (confirmed by reading the source:
`--refs` defaults to `[]` at line 172, and is used unconditionally at line
182 `images = [a.map, *a.refs]` with no guard). It proceeded straight into
`subgen.gen_openai(...)`, which — contrary to the expectation that a missing
`OPENAI_API_KEY` would abort cleanly — actually SUCCEEDED and produced a real
1254x1254 PNG (`.../safe-stop-probe-zero-refs/raw.png`), meaning this
environment/session had a working generation credential path even without
`.secrets/openai.env` sourced in this shell (per repo memory: `subgen
--provider openai` drives the Codex CLI's own subscription-backed image
tool, not the raw `OPENAI_API_KEY` REST path, so it did not need the shell
env var at all). **A real generation call was made and completed before this
executor could intervene — money/subscription-quota WAS spent.** The crash
above happened AFTER generation, in the unrelated metrics step (Finding 4's
shapely failure, silently swallowed).

The exact refusal signal string quoted in the contract, `"style.ref_images
must contain at least one path"`, DOES exist verbatim in this repo — but
only in `studio/packet.py` (`_validate_style`), a schema-validation module
for an unrelated `PanelPacket` JSON pipeline. Nothing in the
`svg-geometry-style-illustration` skill's documented tool chain
(`scaffold_template_task.py` / `svg_geometry_report.py` /
`outset_cutouts.py` / `build_trueaspect_base.py` /
`build_reference_style_packet.py` / `geom_adherence_test.py` /
`export_svg_template_fit.py` / `sync_results_images.py`) imports or calls
`studio/packet.py`. The named safe-stop signal is real code somewhere in the
repo, but it is NOT wired into the generation path this contract's frozen
procedure actually invokes.

**Generation-budget accounting:** this probe counts as 1 of the contract's
"max 2 candidate generations total" — it was a real, completed generation
call, not a dry run. Given Findings 2/3 make the Official Method's real
geometry-conformant `--map` impossible to produce without improvising (which
is forbidden), a second real "candidate" generation would not test anything
different (still no valid outset contract base available) — this executor
did not spend the 2nd generation, per "If generation is impossible... record
as a FINDING and stop."

## Finding 7 — sync_results_images.py is hardcoded to a different, unrelated task

Command:
```
python3 scripts/sync_results_images.py --check
```
Output (exit 0):
```
OK — every result image has a copy in tasks/space-np01-front-bottom-02/RESULTS/Images
```
Read the source: `IMG = ROOT / "tasks/space-np01-front-bottom-02/RESULTS/Images"`
(hardcoded constant) and `sources()` only globs `tasks/space-*/experiments*/`
directories. This task is `tasks/geometry-evidentiary-princess-n02/`, which
does not match `space-*`, so this script is a silent no-op for this task's
results — it did not raise an error, it just checked/reported on an entirely
different, pre-existing task's library and returned exit 0. The skill text
(`svg-geometry-style-illustration/SKILL.md` step 7, "Deliver the chosen raw +
sync ALL results (HARD RULE)") documents this script as a generic
"copy EVERY result image ... into the central library" step usable at the end
of any task run on this skill, but the actual implementation is a one-off
hardcoded to `space-np01-front-bottom-02`. This is a real gap between the
documented (generic) skill step and the actual (task-specific) tool: a cold
executor following the skill step as written gets a silently-misleading
"OK" exit code that has nothing to do with the task just run.
