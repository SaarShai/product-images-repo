# image14-v3 review package
- Source: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png`
- OLD (user-failed) candidate: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/bg-assisted-v2/image14/assisted-r110-vitmatte-decontam/image14-assisted-r110-decontam-rgba.png`
- NEW (fixed) candidate: `/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/bg-assisted-v2/image14/assisted-r110-vitmatte-decontam-c2/image14-assisted-r110-decontam-c2-rgba.png`

## Per-region before/after boards (4x, source | OLD-on-magenta | NEW-on-magenta)
- [01-bubble-x602y130.png](01-bubble-x602y130.png) — bbox [602, 130, 624, 153] — fully deleted translucent bubble
- [02-bubble-x720y284.png](02-bubble-x720y284.png) — bbox [720, 284, 762, 327] — fully deleted translucent bubble (largest)
- [03-bubble-x157y312.png](03-bubble-x157y312.png) — bbox [157, 312, 180, 335] — fully deleted translucent bubble
- [04-coral-scar-x283y402.png](04-coral-scar-x283y402.png) — bbox [283, 402, 292, 408] — coral joint scar nick
- [05-bubble-x116y474.png](05-bubble-x116y474.png) — bbox [116, 474, 136, 494] — fully deleted translucent bubble
- [06-bubble-crescent-x697y647.png](06-bubble-crescent-x697y647.png) — bbox [697, 647, 720, 671] — crescent bubble highlight, part A
- [07-bubble-crescent-x696y660.png](07-bubble-crescent-x696y660.png) — bbox [696, 660, 712, 672] — crescent bubble highlight, part B
- [08-bubble-x834y818.png](08-bubble-x834y818.png) — bbox [834, 818, 858, 843] — fully deleted translucent bubble
- [09-coral-leaf-x292y901.png](09-coral-leaf-x292y901.png) — bbox [292, 901, 300, 910] — small coral leaf tip
- [10-coral-dot-x358y929.png](10-coral-dot-x358y929.png) — bbox [358, 929, 363, 935] — tiny isolated coral dot
- [11-sand-fx-x401y1508.png](11-sand-fx-x401y1508.png) — bbox [401, 1508, 419, 1518] — pale sand-wash accent near hand
- [12-foot-shadow-x434y1606.png](12-foot-shadow-x434y1606.png) — bbox [434, 1606, 450, 1618] — toe shadow on sand

## Edge boards (native-res crop upscaled 8x via Lanczos, PREVIEW APPROXIMATION of print zoom — the real x8 pipeline output is a separate split-render, not this upscale)
- [edge01-fish-translucent-fin--x8preview-4bg.png](edge01-fish-translucent-fin--x8preview-4bg.png) — native bbox [520, 595, 560, 650], upscaled 8x (Lanczos preview)
- [edge02-known-fringe-pink--x8preview-4bg.png](edge02-known-fringe-pink--x8preview-4bg.png) — native bbox [518, 593, 560, 652], upscaled 8x (Lanczos preview)
- [edge03-right-pale-seaweed--x8preview-4bg.png](edge03-right-pale-seaweed--x8preview-4bg.png) — native bbox [770, 660, 840, 730], upscaled 8x (Lanczos preview)
- [edge04-bubble-x720y284-rim--x8preview-4bg.png](edge04-bubble-x720y284-rim--x8preview-4bg.png) — native bbox [710, 274, 772, 337], upscaled 8x (Lanczos preview)

## Full four-background board (NEW candidate)
- [full-four-backgrounds-NEW.png](full-four-backgrounds-NEW.png)

## Known deferred defects (not fixed in this candidate)
Independent re-derivation of the deleted-paint map found 14 components >=16px
(superset of the 7 user-flagged regions). Two of the smallest (16px coral-tip
nick at bbox [532,687,542,695]; 26px coral leaf-tip nick at bbox
[584,880,591,886]) sit within the fixed correction_unlock_radius_px=110 of
legitimate transparent paper gaps between coral branches
(bg-interior-gap-cut02, edge-known-fringe-pink). Correcting them reopened
those gaps to the matting solver and caused it to bleed alpha into
previously-correct transparent pockets — a measured regression, confirmed via
an unlock-radius sweep (24px also tried; it broke a different, unrelated
guard and the rgb-reconstruction check instead, so a smaller radius is not a
safe fix either). These 2 defects are intentionally left uncorrected to avoid
a demonstrated regression; the other 12 (including all 7 originally known)
are fixed and pass the independent benchmark cleanly.
