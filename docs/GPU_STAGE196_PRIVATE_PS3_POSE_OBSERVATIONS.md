# Stage 196 — private original-PS3 observation alignment (not an authenticity claim)

## Purpose

Stage 195 demonstrated that the independent C and Python research pipelines
agree on 810 components of **invented** multi-root animation poses.
Agreement of two research implementations does not prove original PS3
coordinate conventions, bind correction, exact character/clip identity or
authentic game movement.

Stage 196 provides a **purely offline**, privacy-preserving method to compare
operator-annotated visible pose silhouettes from **two separately acquired
captures**: original PS3 game playback and the experimental Switch wireframe.
It does **not** capture footage, operate the PS3, drive NeXium, compare raw
images, or independently authenticate the screenshots and their timestamps.

Only locally available/authorized observations may be used. **Do not
upload original game screenshots, original PS3 models/BANIM, captures or
any annotation file to GitHub or a public CI artifact.**

## Setup: a deliberately blank observation ledger

```sh
mkdir -p local-data/observations
python3 -m tools.foj_stage196_private_pose_observations \
    --init local-data/observations/pose-landmarks.json
```

The new JSON is an empty private template with both
`capture_recorded=false` and no frames. The initializer refuses to
overwrite an existing record. An empty template **cannot** pass analysis.

Independently acquire actual, authorized playback captures for both the
original game and the experimental viewer using the same visible character,
camera angle, pose and local animation timestamps, preferably three or more
frames. The current package does **not** contain such matched captures.
Record the acquisition method separately, locally. The
`capture_recorded` values are **operator assertions**, not evidence
verified by this utility.

Enter 3–12 chronological matched frame pairs. Each frame needs 4–32
**distinct, non-collinear** and identically named landmarks (e.g.,
head, elbow, hand, ankle) consistently present across all frames.
Mark each point in normalized image coordinates (`x / image_width`,
`y / image_height`), each within 0..1. Landmarks must refer to the
same anatomical/visual point; a mesh vertex index is not automatically
a valid source-game landmark. Respect perspective, camera focal length,
character orientation and occlusion.

Example **structural illustration** (all coordinates invented):

```json
{
  "schema": "foj.stage196.private_pose_landmarks.v1",
  "ps3_observation": {
    "source_kind": "original_ps3_playback",
    "capture_recorded": true,
    "timestamp_method": "manual_timestamp",
    "timing_uncertainty_seconds": 0.02
  },
  "experimental_observation": {
    "source_kind": "experimental_switch_research",
    "capture_recorded": true,
    "timestamp_method": "manual_timestamp",
    "timing_uncertainty_seconds": 0.02
  },
  "frames": [
    {
      "ps3_time_seconds": 0.0,
      "experimental_time_seconds": 0.0,
      "landmarks": [
        {"id": "head", "ps3_xy": [0.4, 0.2], "experimental_xy": [0.5, 0.22]},
        {"id": "hand", "ps3_xy": [0.6, 0.35], "experimental_xy": [0.68, 0.32]},
        {"id": "hip", "ps3_xy": [0.43, 0.55], "experimental_xy": [0.53, 0.56]},
        {"id": "ankle", "ps3_xy": [0.5, 0.8], "experimental_xy": [0.6, 0.81]}
      ]
    }
  ]
}
```

The illustration intentionally contains only **one frame** and is
therefore not a valid completed observation. Build your own genuinely
observed sequence; do not fabricate additional observations.

The comparator rejects unsorted, duplicate or unmatched frame/point
identities, repeated JSON keys, nonfinite numeric values, a timestamp
mismatch larger than the *sum of declared acquisition uncertainties +
1 ms*, and degenerate/collinear point sets. The 1 ms numerical slack is
not a promise of emulator timing accuracy.

## Analyze privately

```sh
python3 -m tools.foj_stage196_private_pose_observations \
    --analyze local-data/observations/pose-landmarks.json \
    > local-data/observations/pose-alignment-private.json
```

It fits each pair of frames using a 2D **scale + in-plane rotation +
translation** transform (least-squares similarity alignment), then
reports shape residual RMS divided by the reference landmark radius.
An alternative fit mirrors the horizontal axis before the same
alignment. This is a **diagnostic competing hypothesis**, not an
automatic coordinate handedness selection. It also reports temporal
changes in pairwise landmark distances, normalized by each frame's
landmark radius, which are invariant to 2D translation/in-plane rotation
and uniform scale.

The report contains rounded residual arrays and aggregate counts,
never original images, annotations, landmarks, user identifiers,
original file names, capture paths, per-bone transforms, movie frames
or source hashes. All evidence/authenticity flags remain `false`.
Even this summary may disclose asset-specific metrics: **keep it
private**.

### Interpretation constraints

- An ordinary-fit error near zero means the **marked 2D points** look
  similar after nuisance alignment; it says nothing about hidden depth,
  texture/materials, exact clip provenance or PS3 bone math.
- A lower mirrored-fit residual **does not prove** opposite handedness:
  view direction, camera, point labeling, or character symmetry could
  explain it.
- Per-frame realignment can hide camera motion and root translation:
  a low shape residual is not evidence that timing or root motion match.
- The temporal metric helps detect shape evolution differences across
  the marked frames but cannot identify the source engine's state graph.
- `capture_recorded=true` is only an operator claim. The comparator
  cannot authenticate hardware capture or guarantee footage is from the
  original PS3. Physical Nintendo Switch test evidence is also absent.

## Testability and privacy

`tests/test_foj_stage196_private_pose_observations.py` contains 16
invented-only Python cases: correct in-plane alignment, mirrored
diagnosis, disturbed landmarks, temporal deformation, time mismatch,
bad IDs, nonfinite coordinates, degenerate geometry, duplicate JSON
keys, corrupt private file and CLI failure without private-path leakage.

Public GitHub Actions exercises only these synthetic fixtures.
No proprietary game assets, original screenshots, animation curves or
user-owned observation files are in the repository.

**Next evidence requirement**: the operator must produce actual,
timestamp-matched authorized original-game and experimental captures
privately, document any camera/perspective mismatch, then run this
local ledger analysis. Even with a good numerical comparison, a
separate independent observation is required before declaring a
recovered PS3 animation convention.
