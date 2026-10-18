# Stage 206 — owner-private visual review of two-sided pose annotations

Stages 203–205 established a chain for **local, owner-authorized** data:

- Source PS3-side frames supplied by the operator and tied to manual
  source landmarks by exact PNG bytes, private SHA-256 manifest,
  dimensions and operator timestamps (Stage205).
- Experimental-side points checked against actual native C-rendered
  FOJRM001/BANIM PPM wireframes, by named frame and 10-pixel proximity
  (Stage204).
- Experimental rig/clip intake, pose diagnostics and source-vs-research
  2D shape comparison (Stages 195–203).

**Missing piece:** a person could not easily inspect both image sides
with *the same numbered landmarks* and discover incorrect bodypart
names, dissimilar camera views or false temporal pairing. Stage206
adds a **private visual inspection output**, without calling any
external services, using Pillow or uploading protected content.

## New output: original and research overlays

`tools/foj_stage206_private_pose_review.py` decodes the owner-local
source PNG and research PPM at their respective **native resolutions**.
It draws numbered magenta crosshairs at the annotated source and
experimental coordinates, in identical anatomical-label order.
`PRIVATE_landmark_number_key.json` maps 1..32 to operator landmark
names. It is a private file: labels and overlays are **never**
printed on stdout or uploaded to public CI.

The standalone invocation is:

```sh
python3 -m tools.foj_stage206_private_pose_review \
  --observations local-data/observations/pose-landmarks.json \
  --source-manifest local-data/observations/source-png-private.json \
  --source-dir local-data/observations/ps3-frames \
  --research-bindings local-data/observations/native-frame-binding.json \
  --research-dir local-data/stage203-private-evidence/private-frames \
  --output-root local-data/stage206-PRIVATE-visual-review
```

Or regenerate the entire owner-private actor diagnostic bundle using
the existing Stage203 command **plus** all source- and research-side
binding flags and the new `--review-overlays` option:

```sh
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --observations local-data/observations/pose-landmarks.json \
  --source-png-dir local-data/observations/ps3-frames \
  --source-png-manifest local-data/observations/source-png-private.json \
  --frame-bindings local-data/observations/native-frame-binding.json \
  --review-overlays \
  --output-root local-data/stage206-PRIVATE-bundle
```

The `private-two-sided-review` directory within the bundle contains
`source_000_REVIEW_PRIVATE.png`, `research_000_REVIEW_PRIVATE.png`,
etc. The corresponding numbered annotations appear on both. It
also saves a private per-number anatomical key and a minimal report
whose authenticity flags are explicitly **false**.

The tool checks **both upstream input bindings before drawing** and
rechecks source-image identity and experimental wireframe proximity
after all images are drawn. New output locations must be empty,
owner-only and, when inside the Git repository, placed beneath its
ignored `local-data/` directory. If any check fails, only the newly
created partial output is deleted; existing operator source files and
prior evidence are not modified.

### What the human reviewer should look for

Compare each matching pair at its **native aspect ratio**:
the same numbered mark should refer to the *same visible part* of the
correct character in both images. Inspect whether camera pitch,
perspective, actor facing and occlusion make the pair comparable.
A mark touching an arbitrary wire can pass the 10-pixel code check
without being anatomically correct. Pay particular attention to
hands/feet swapping sides, wrong animation states and clip B fades.

Review a sequence, not just a single attractive frame: static or
repeating movements can produce false 2D correspondence and timing
estimates. Document uncertain matches privately and obtain an
independent second observation when necessary.

**Important:** Creating overlays is **not** equivalent to conducting
human review. The generated report always says
`manually_reviewed_by_human=false` and
`correct_anatomical_landmarks_confirmed=false`. Only a person
examining owner-authorized original-game captures can assess those
aspects, and even that does not cryptographically authenticate PS3
hardware or prove original engine bone math.

### Decode and privacy limits

The source decoder uses the Stage205 bounded 8-bit RGB/RGBA,
noninterlaced PNG format checks and implements PNG filters 0–4.
Alpha is composited on white. Original dimensions are preserved; the
480×320 research wireframe is never stretched to match a source
screenshot. Rendered annotated images use plain 8-bit RGB PNG with
private (mode 0600) files in a mode-0700 directory.

This program is local, deterministic and requires no network or
Pillow. It **does not automatically identify landmarks** and cannot
legitimately run on real owner-held images in public GitHub Actions.

Test `tests/test_foj_stage206_private_pose_review.py` exercises
invented source RGB/RGBA PNGs, all five PNG filters, alpha handling,
numbered overlays and private anatomical keys, swapped/corrupt
source and research images, no-overwrite behavior, protected CLI
outputs, and the full **production C** rig/BANIM renderer with
generated-only original-side PNGs.

## Evidence still absent

No authentic original FoJ PS3 captures were received in this
public CI. No original game character identity, original animation
pose mathematics, source camera or temporal match is authenticated.
Generated images are only **visual aids for owner-private review**.
They may contain copyrighted game artwork once run on real user
assets and therefore must **never be posted to GitHub or uploaded**.
