# Stage 215 — lock the owner-selected C research camera before annotation

Stage213 added bounded native C camera settings, and Stage214 renders
2–9 research views on the same private rig/animation clips into an
owner-only comparison sheet. After inspecting this sheet, operators
must **lock the chosen camera** before annotating source-game and
research images. Otherwise a later camera change can make the
comparison irreproducible or hide unexpected pose discrepancies.

Stage215 adds an owner-local selection lock and a **nine-state
byte-for-byte verification** against the final Stage203 native
research render. It checks that the actual C-produced wireframe
geometry, *not just metadata or yaw/pitch/zoom text*, matches the
operator's chosen Stage214 candidate. Stage215 also pins the
exact staged rig and BANIM bytes across both runs.

## Owner-local workflow

First run Stage214's multiple-view experiment using an
owner-controlled rig and BANIM files kept outside public CI.
Inspect `private-camera-contact-sheet.ppm` and select a candidate
index from the protected `private-camera-view-index.json`.

### 1. Lock the selected view

```sh
python3 -m tools.foj_stage215_private_camera_choice_lock \
  --lock \
  --preview-root local-data/stage214-PRIVATE-camera-choices \
  --view-index 1 \
  --lock-file local-data/PRIVATE-selected-research-camera.json
```

The tool verifies the complete Stage214 contact sheet against
the **actual** native C `play_025.ppm` pixels in all camera tiles.
It validates the view index, exact camera coordinates, nine expected
PPM state images, pause/reset invariants and default C-host rig
state. Then it creates a new mode-0600 **private** lock containing
the selected camera and SHA-256 for its nine native frames and the
sheet, as well as SHA-256 hashes of the staged rig and BANIM files.
The asset digests use a single no-follow file descriptor per file and
reject symlinks, nonregular nodes and out-of-bounds file lengths.
These hashes and camera parameters are **never printed**.

The choice is operator-supplied, not selected using image-plane
fidelity scores or backfitted to the observation data.

### 2. Render the final research comparison using Stage203

Use the saved yaw, pitch and zoom from
`private-camera-view-index.json` with the **same owner-local
FOJRM001/BANIM**:

```sh
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --camera-yaw -0.65 \
  --camera-pitch 0.4 \
  --camera-zoom 0.86 \
  --output-root local-data/PRIVATE-final-native-camera
```

These numbers are just an example from the Stage214 experiment.
Select and use your *actual* locked settings; do not assume these
are correct for any original PS3 camera.

### 3. Verify exact native C frame identity

```sh
python3 -m tools.foj_stage215_private_camera_choice_lock \
  --verify \
  --preview-root local-data/stage214-PRIVATE-camera-choices \
  --lock-file local-data/PRIVATE-selected-research-camera.json \
  --stage203-root local-data/PRIVATE-final-native-camera
```

Verification checks the lock against the original Stage214
contact-sheet bytes, original view metadata, and all original nine
PPM frames, and independently reads Stage203's private
`private-research-camera.json`. It requires exactly the locked
camera and the **same pixels** in every Stage203 research frame.
It also requires byte-identical staged rig/BANIM input files, including
the presence or absence of the optional second clip.

A modified staged rig or clip, missing optional secondary clip,
changed view, altered pixel, swapped research frame, edited
camera manifest, wrong zoom or different actor/animation rendering
causes the audit to fail. Files and previous locks are never
overwritten or copied into public CI.

Once verified, perform Stage204/205 image-binding and Stage206
anatomical visual review against the *final* locked Stage203 frames.
Do not change research projection or clip playback between
camera-selection and manual landmark annotation. If the view or source assets must
change, start with a **new private Stage214 preview and new lock**.

**Lock schema v2:** v1 private lock files lack source-asset hashes and
will be rejected. Create a fresh owner-private Stage214 preview and
lock rather than modifying the old record.

## Privacy and provenance

This is a private reproducibility check. The native C frame and
source-data hashes may be proprietary and must remain under
`local-data/` or another owner-only private directory. The
tool only writes a private lock when requested, never uploads
original assets, and never emits geometry, hashes, camera options
or file locations on stdout.

The lock is not digitally signed or independently witnessed.
It **cannot authenticate original PS3 hardware/gameplay**, confirm
which source game character or clip was captured, measure genuine
PS3 camera projection, or verify bone transforms or animation
timing. It only shows that the two *local research C render runs*
are byte-identical for the selected candidate.

## Synthetic CI

`tests/test_foj_stage215_private_camera_choice_lock.py` uses
generated-only FOJRM001/BANIM files and actual production C
rendering in Stage214 and Stage203. It tests a correct nine-frame
match, wrong camera refusal, altered preview/final PPM pixels,
tampered view metadata, descriptor-pinned asset hashing,
symlink/FIFO rejection, changes to staged input bytes,
secondary-clip removal, exact view index ordering, existing lock
protection, private file permissions and CLI path/hash secrecy.
No commercial PS3 game media enters the repository or Actions.
