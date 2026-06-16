# Global agent rules (all codex sessions)

## Filesystem safety in `~/Documents` (Google Drive synced)

`~/Documents` is continuously synced by Google Drive Desktop. On 2026-05-29 a
codex "Drive Relief" job relocated 17 projects' `.git` directories out of
`~/Documents` while Drive was mid-sync; Drive then created conflict copies and
renamed a live project folder (`Master Screenery 3.5` -> `Master Screenery copy`).
The user experienced this as a folder "disappearing". Do not repeat it.

1. Never move, rename, or delete a folder or a `.git` directory inside
   `~/Documents` without explicit, per-action user confirmation. This explicitly
   includes "sync relief", relocating `.git`/heavy dirs out of the tree,
   "cleanup", or "repair" operations. State the exact command and wait for a yes.
2. No mass/recursive filesystem operations across multiple `~/Documents`
   project folders. One folder, one confirmed action at a time.
3. Do not attempt to "fix" Google Drive sync by reorganizing the filesystem.
   Report the situation to the user and let them decide.
4. Before any structural change, check for active sync:
   `ls ~/Documents/.tmp.driveupload | wc -l` (a backlog = sync is busy = do not
   make structural changes).
5. Treat `* (1).ext` files and ` copy` folder suffixes as Google Drive conflict
   artifacts, not authoritative versions.

## Image-generation iteration: reset vs. patch

When a result is imperfect or needs improving, do not assume the next step
should be another edit or repair pass on that same result. Treat the latest
output as evidence. Before continuing from it, consider whether the accumulated
feedback and task learnings should instead be folded back into the source prompt
and used for a fresh generation from the original references/templates.

Decide case by case. If revising the prompt would make the next attempt clearer,
cleaner, or less constrained by earlier mistakes, prefer restarting from that
revised prompt over trying to rescue the most recent output. If continuing from
the current result is still the better path, make that choice deliberately.

## Template-fit repair learning

For Baci-door or similar SVG-constrained image-generation work, recover from the
actual task folder and latest artifacts before generating again. Treat SVG
geometry as authoritative, including polygon cutouts, and verify with the local
parser/export tooling rather than screenshots or filenames alone.

For Baci-style hole-section repairs, use the repo-local skill at
`.codex/skills/baci-template-fit-repair/SKILL.md`. A template-fit `PASS` is only
the mechanical gate: still review the hole crop and full-frame export. When the
main artwork is good but the cutouts are scarred, prefer bounded local donor
repair plus exact SVG cutout cleanup over broad inpaint or repeated prompt-only
nudges.
