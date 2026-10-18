# Stage 213 — adjustable camera for the native rigged-actor C renderer

The original Stage200/203 production C actor host always rendered
experimental FOJRM001/BANIM wireframes using fixed camera parameters
`yaw=0.5`, `pitch=0.2`, `zoom=1.0`. Source PS3 gameplay may have
different actor facing and camera orientation; comparing a single
hard-coded experimental view can make perfectly legitimate poses look
wrong.

Stage213 adds **bounded operator-controlled native rendering
parameters**. The result is a research projection, not a recovered
original game camera. No PS3 game assets, reference captures, view
matrices or imported images are stored in public CI.

## Owner-local use

Run Stage203 as before, optionally selecting a view:

```sh
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --camera-yaw -0.65 \
  --camera-pitch 0.40 \
  --camera-zoom 0.86 \
  --output-root local-data/stage213-PRIVATE-camera-view
```

Default options remain exactly `0.5, 0.2, 1.0`, so existing
generated NRO research behavior and every Stage203 host camera
remain unchanged unless options are explicitly supplied.

Limits: yaw −π..+π, pitch −1.4..+1.4 radians, zoom
0.25..3.0. NaN, Inf, booleans and invalid numbers are rejected
**before creating an evidence directory**. Native C independently
parses and validates the numeric arguments to prevent bypasses.
A zoom/framing choice may legitimately fail to display six wire
pixels, in which case the entire new local output is rejected and
removed.

The actual production C `foj_obj_wireframe` is now called with
the selected camera for all nine evidence frames. No image is
cropped/reprojected after the fact. The existing pause/reset,
source skinning and A→B crossfade checks still apply.

On successful execution, the owner-only
`private-research-camera.json` records the **actual research view
settings passed to native C**. It explicitly keeps
`original_ps3_camera_authenticated=false` and
`source_game_view_equivalence_verified=false`. This information
is not included in public stdout. As usual, even aggregate reports
and any PPM or FOJRM001/BANIM files must remain private.

## Why this matters for genuine PS3 comparisons

Use Stage206's paired annotated overlays to compare identical body
parts while iterating a plausible research camera orientation. Do
not stretch the 480×320 experimental raster to match the source
screen capture. Only annotate the **native frames rendered under
the final selected camera** and bind their PPM pixels using Stage204.

An apparently improved 2D match after adjusting yaw/pitch/zoom is
only a research hypothesis: the original PS3 engine may use a
different projection, bind pose, character root transform, scale,
bone hierarchy and animation sample time. Stage207/208 can help
identify unresolved projection nuisances but cannot solve these
authenticity problems.

It is important to note that current wireframe rendering is a
**diagnostic orthographic-like view**, not a faithful clone of the
original game's perspective camera. Its zoom is a screen-space
scale, not a physical focal-length measurement. These options do
not change the real Switch NRO camera yet: Stage213 modifies the
separate owner-local Stage200/203 native **C host viewer**, not the
Switch application's on-device interactive camera.

## Generated-only regression tests

`tests/test_foj_stage213_private_native_camera.py` runs the actual
production C rig/player/skinning renderer with generated-only
FOJRM001 and dual BANIMs; checks nine frames differ for a changed
camera, confirms pause/reset state invariants, verifies owner-only
view metadata, rejects invalid camera options before output,
tests legacy native two-argument invocation, rejects invalid direct
C camera arguments and ensures CLI does not expose owner paths.

Public CI contains no original PS3 captures, commercial rig data,
game resource bytes, camera metadata or owner-private reports.
