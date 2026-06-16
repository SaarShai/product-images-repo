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
