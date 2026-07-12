# ComfyUI SAM 3.1 image14 execution lane

**Run date:** 2026-07-10

**Outcome:** the lane is permanently blocked at checkpoint transfer. The initial official transfer received zero bytes; the one parent-authorized transport retry reached the official CDN and received 1,305,342,008 bytes before the connection reset. The incomplete `.part` failed the fixed size/SHA gate and was removed. No model was installed and no candidate was generated.

## Versioned execution spec

- Held pre-execution v1.0 SHA-256: `65115cd1679447e2a43f00cce9da486dc9b5bc7a8277ebbc9cd2dc11e0be96a0`.
- Executable v1.1 SHA-256 before the attempt: `1323f216cfd01590109d312c7c8b5f023c8859807c1bddff43f86e5d4048df1b`.
- v1.1 changed only the user-directed output root and `--correction-unlock-radius 6` → `110`; the SAM points, five-node graph, thresholds, checkpoint, MPS device, frozen verifier, and `max_iterations=1` stayed fixed.
- Radius evidence: the fresh prior `assisted-r110-vitmatte/metrics.json` records radius `110`; its frozen `fg-sand-watercolor-wash` guard passed at fraction `1.0` and median alpha `168`, and all 26 frozen sure-FG/exterior-BG/enclosed-BG guards passed. That prior candidate still failed two white-edge probes, so the evidence justified correction transport only and did not weaken or replace this lane's edge gates.
- Fresh lint after amendment: `loop-lint ... OK`, `0 fail · 0 warn`; all ten Bash blocks, three embedded Python programs, and the five-node API JSON parsed.

## Frozen preflight that passed

- Source: 941×1672 RGB, SHA-256 `925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d`.
- Corrections: 941×1672 RGBA, SHA-256 `18d695a2cada3a2e1fb9a7c72f2ec04ed90a9e89d6dfc1d8d96a73bd47ab6a61`.
- Point contract: 15 positive and 10 negative points passed the frozen class assertions.
- Extracted API graph SHA-256: `557ecf896756cada8391c3a4202714463b9cf16ebdd82d29db31e94f640fd77d`.
- ComfyUI HEAD before and after: `a590d60bb1d7d47c1cdb49fc8116b0e919fc4bd1`; worktree clean.

## Blocking download evidence

The initial transfer used the official Comfy-Org URL:

```text
started_utc=2026-07-10T11:37:35Z
curl: (28) SSL connection timeout
http_code=000
bytes_downloaded=0
seconds=30.002198
curl_exit=28
actual_size=absent
actual_sha256=absent
finished_utc=2026-07-10T11:38:05Z
verdict=BLOCKED_DOWNLOAD_OR_CHECKSUM
```

The final checkpoint and `.part` path are both absent. The preserved raw log is:

`/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/comfyui-sam31-image14/model-download.log`

Raw-log SHA-256: `eeac87d7e252af3496017d20031af74a36b05df81ab108984cece6b13e24504b`.

The parent loop then authorized exactly one transport retry with a 300-second connection timeout and no curl retry flag. It used the same official URL and reached the official Hugging Face Xet CDN:

```text
attempt=2_authorized_transport_retry
started_utc=2026-07-10T11:48:10Z
curl: (56) Recv failure: Connection reset by peer
http_code=200
bytes_downloaded=1305342008
seconds=293.998603
curl_exit=56
actual_size=1305342008
actual_sha256=60768dcf617df8c5355b6568c5883c5024cadf78ffc30e008877382f303ecbbe
finished_utc=2026-07-10T11:53:07Z
verdict=BLOCKED_SECOND_TRANSFER
partial_cleanup=PASS_absent
```

The retry raw log is `Images/candidates/comfyui-sam31-image14/model-download-retry.log`, SHA-256 `6361fd7bfbb74830368cbe8ee18ff12bb307397bb6c055fc5e78ca335487173e`.

Source, downloadable-file SHA-256, Xet hash, and SAM License metadata are preserved in `MODEL-SOURCE.json`.

## Stop-boundary proof

- No `sam3.1_multiplex_fp16.safetensors` or `.part` file exists.
- No Comfy `main.py` process or listener on 8188, 8198, or 8199 exists.
- No graph submission, MPS inference, ViTMatte run, CPU fallback, threshold change, text prompt, candidate, benchmark invocation, final, or commit occurred.
- The frozen benchmark manifest remains at SHA-256 `55a0b0283b8223154fafe3120f900ac662167279199c2d5a05b34f8f2dfdf2f1`, with mtime `2026-07-09T21:35:34Z`.
- Product output contains only `workflow-api.json`, `point-contract.log`, `model-download.log`, and `model-download-retry.log`; no candidate or visual board exists to judge.

**STATUS: FINAL NETWORK BLOCKER; SECOND TRANSFER FAILED CLEANLY, NO CANDIDATE GENERATED.**

**READY FOR JUDGING.**
