# Stage 214 — owner-private native C camera comparison sheet

Stage213 makes the **real local production C rigged-actor renderer**
accept yaw, pitch and zoom. The next practical task is evaluating
several plausible views of the **same local actor and animation
inputs** before manually assigning original-game landmarks. Running
them one at a time risks mixing cameras, clips and outputs.

Stage214 compiles the real C renderer once, uses one fixed owner-local
FOJRM001 rig plus one/two BANIM clips, generates the same nine state
frames per camera and assembles a private visual comparison contact
sheet. It is **an inspection tool, not a PS3 camera solver**.

## Owner-private command

Run on an owner-controlled computer with the user's locally exported
rig and animations:

```sh
python3 -m tools.foj_stage214_private_multicamera_preview \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --camera=.5,.2,1 \
  --camera=-.65,.4,.86 \
  --camera=.75,.1,1.15 \
  --output-root local-data/stage214-PRIVATE-camera-choices
```

The `--camera` values are `yaw,pitch,zoom`; use between **two and nine
distinct choices**. Angles are in radians. The accepted bounds are
yaw ±3.1415926, pitch ±1.4, zoom 0.25–3.0. NaN, Infinity, duplicate
views, malformed arguments or invalid models/animation clips are
rejected before creating output. No original game resources belong
in public CI.

### Private outputs

- `private-switch-sd/`: only the owner's protected local inputs.
- `private-actor-host-smoke`: one native C executable, compiled once.
- `private-camera-frames/view-00/`, `view-01/`, etc:
  nine unmodified actual C-rendered PPM state images per choice.
- `private-camera-contact-sheet.ppm`: up to three columns of
  **actual** 480×320 `play_025` C frames, visually side by side;
  blank cells use the research renderer's background. It copies
  the native pixels; the tool does not synthesize or redraw geometry.
- `private-camera-view-index.json`: index-to-camera settings and
  private playback-state checks. Use it to choose a camera and to
  reproduce the exact view later with Stage213.

Everything is created under a **new**, mode-0700 private directory;
image and metadata files use mode 0600. Existing private outputs
are never overwritten. On a rejected run, only the newly created
partial output is cleaned up. No camera settings, image pixels,
owner paths, source hashes or animation values are printed to
stdout or uploaded.

## After choosing a candidate view

Select the preferred camera based on private examination of
owner-authorized gameplay and actual C-rendered previews. Then
re-run Stage213/203 with the **exact chosen camera** and annotate
landmarks on that final research output before Stage204/205
image-identity binding, Stage206 two-sided visual review, and
Stages207–212 comparisons.

**Do not** automatically select the best-looking alignment on the
same points that will later be used to claim agreement. A distorted
research camera could hide rig, animation or anatomy errors. Use
separate scenes or held-out annotated landmarks where possible.
Camera parameters in this orthographic-like research renderer are
not the original FoJ camera matrix, field of view or perspective
calibration. All PS3 camera, animation and gameplay-authenticity
fields stay false.

## Generated-only tests

`tests/test_foj_stage214_private_multicamera_preview.py` checks
actual production C rendering of multiple views on a generated
rig/dual-BANIM input, all nine states, visible frame differences,
pause/reset reproducibility, byte-exact mosaic tiling, private
permissions and nonleaking reports, single-clip compatibility,
invalid/duplicate camera settings, and output non-overwrite.
It requires no original PS3 files and never writes original-game
assets or screenshots to public GitHub.
