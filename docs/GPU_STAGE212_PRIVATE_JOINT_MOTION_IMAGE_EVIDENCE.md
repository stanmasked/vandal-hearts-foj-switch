# Stage 212 — a single owner-private gate for image and motion evidence

This stage **combines** two existing independent diagnostics:

1. Stage210: operator-declared two to four annotated motions, per-window
   2D articulated transition consistency, and duplicate normalized
   trajectory detection.
2. Stage211: separately collected owner-local source PNGs and C-viewer
   research PPM frames for each window, exact source bytes in private
   manifests, actual research-wire landmark proximity, and detection
   of duplicate source images between nominally distinct actions.

Stage212 does not invent a new PS3 authenticity test. Its job is to
prevent either a plausible animation **without source images**, or
separate valid images **without coherent independent movement**, from
being presented as combined evidence.

## Owner-private usage

With an existing Stage199 schema motion-window observation JSON and a
Stage211 owner-local image-bindings JSON, run:

```sh
python3 -m tools.foj_stage212_private_joint_evidence \
  --observations local-data/observations/motion-windows-private.json \
  --bindings local-data/observations/window-image-bindings.json \
  > local-data/observations/PRIVATE-stage212-joint-evidence.json
```

This command works offline on the owner's computer, does not generate
or upload any images, and never prints private file paths, image hashes
or raw landmark coordinates. **Even the aggregate report is private.**

The program checks every window's source PNG bytes and research PPM
landmarks, computes the motion consistency audit against **the same
in-memory observation document**, and then checks the source and
research images again to narrow file-replacement races. An input
file changed after the operation finishes is not protected by this
method; a secure owner-controlled storage and independently captured
media are still required for stronger provenance.

The combination will only reach
`tentative_joint_local_2d_consistency_only` if *all* of these hold:
- no PNG is replayed across image windows;
- all normalized source/research motion trajectories differ;
- each window contains informative, coherent 2D articulated movement;
- the operator has declared distinct actions and both capture streams;
- the timestamp-interval diagnostics do not conflict.

All other scenarios are explicitly downgraded, including duplicate
motion, duplicate original-side screenshots, missing capture
declarations, static motion, anomalous time intervals and incompatible
annotations. A corrupted, substituted or missing image or an invalid
landmark stops the entire audit with a generic error.

## Evidence limitations

This is **not** confirmation of an original-game port or animation
reconstruction. A good 2D landmark comparison cannot verify:
- that PNG captures originate from *Vandal Hearts: Flames of Judgment*
  running on actual PlayStation 3 hardware;
- whether the source and research models represent the same character,
  animation clip, skeleton, joint label or camera;
- 3D bone transforms, authentic gameplay logic or frame scheduling;
- actual independence of distinct recordings or original PS3 timing.

Even a tentative status keeps **every original PS3 authenticity and
animation-fidelity flag false**.

Use owner-authorized genuine source recordings and inspect paired
Stage206 overlays privately to resolve camera occlusion, anatomy,
character identity and timing. Do not upload original game captures,
PKG files, decrypted animations or model exports to GitHub.

## Generated-only regression checks

`tests/test_foj_stage212_private_joint_evidence.py` creates only
synthetic 8-frame joint trajectories, independently fabricated RGB/RGBA
PNG source images and synthetic PPM wire-mark frames. It verifies a
two-sided coherent case, duplicate PNGs with independently changing
motion, identical motion with distinct PNGs, missing operator
declarations, static sequences, corrupted sources or landmarks,
nonmutation of private input, and path-free CLI success/failure.

The Stage210 and Stage211 components also have their own separate
synthetic test suites. Public CI exercises **generated-only data**;
real PS3 input has not been examined or authenticated.
