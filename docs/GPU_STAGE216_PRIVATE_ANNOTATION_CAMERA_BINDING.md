# Stage 216 — bind private annotations to a locked research camera

This is an **owner-local repeatability guard**, not a recreation of original
PS3 camera metadata or proof of original-game animation fidelity.

Dependency status: Stage215 v2 is merged into `main`. Stage216 is
reviewed and tested as a separate PR against that merged base; the
Stage215 lock receipt format remains version 2.

Stage215 v2 already pins the Stage214 preview sheet, selected yaw/pitch/zoom,
all nine exact native C PPM frames, and the staged rig and BANIM byte hashes
against Stage203. Stage216 adds the *specific annotation evidence* used with
that chosen view. It validates the existing Stage204 research-wireframe
landmarks and Stage205 private source PNG manifest, then commits hashes of
the operator observations, frame labels, source manifest, camera selection
lock and final Stage203 camera receipt to a mode-0600 owner-private JSON.

All images, source PNG hashes and human-made coordinates stay private.

## Procedure

1. Generate Stage214 candidate views with your local, owner-controlled rig
   and clips. Choose a view **before annotating** any original-game frames.
2. Run Stage215 v2 --lock, then Stage203 with those exact camera arguments.
   Run Stage215 --verify. Keep the preview, render and source files unchanged.
3. Create private Stage196 observations, Stage204 frame labels and Stage205
   PNG manifests using only locally obtained materials. Source captures and
   their claimed PS3 origin are **not authenticated** by these tools.
4. Bind the analysis files to the locked native research render:

       python3 -m tools.foj_stage216_private_annotation_camera_binding \
         --bind \
         --preview-root local-data/PRIVATE-stage214 \
         --camera-lock local-data/PRIVATE-camera-lock.json \
         --stage203-root local-data/PRIVATE-stage203 \
         --observations local-data/PRIVATE-operator-marks.json \
         --frame-bindings local-data/PRIVATE-frame-labels.json \
         --source-manifest local-data/PRIVATE-source-manifest.json \
         --source-dir local-data/PRIVATE-source-pngs \
         --binding-receipt local-data/PRIVATE-camera-annotations.json

5. Later, run the same command with --verify instead of --bind. The receipt
   must already exist and the native frames, selected camera, asset files,
   annotated coordinates, frame-label manifest, source PNG manifest and
   original PNG image bytes must still match. The tool never overwrites the
   previous receipt. The tool also pins the receipt's own raw bytes for
   the whole revalidation and rejects an in-flight replacement, even one
   that only alters JSON whitespace. For a legitimate change, create a
   new private comparison with a different receipt.

### Rejection cases

- Swapped selected camera, modified zoom, edited Stage215 lock, modified
  Stage203 camera receipt, native pixels or staged FOJRM001/BANIM bytes.
- Rewritten observation landmark coordinates, private frame-label manifest
  or source PNG manifest (even if some semantic values remain identical).
- Incorrect Stage204 frame-to-wire correspondence or invalid timestamps
  and correspondence geometry; changed/missing Stage205 source PNGs.
- Operator metadata that does not declare both capture sequences recorded.
- Pre-existing output receipt, malformed input schemas and symlinked
  private JSON input files, including a symlinked receipt. Input digests
  are read from a single no-follow descriptor, avoiding a separate
  pathname lookup after checking the file type.
- Any mutation of the receipt's raw bytes during verification, including
  semantically equivalent JSON formatting changes.

All public console messages are aggregate status only; the private lock
contains exact file hashes and is **not for GitHub, public CI, logs or
screenshots**. A record alone is not a digital signature, independent
timestamp or independent validation of purported PS3 gameplay. The
original-camera match and animation-fidelity flags remain **false**.

## Synthetic tests

The Stage216 test module creates an invented FOJRM001 rig and BANIM clips,
actually renders Stage214 and Stage203 frames using the production C host
renderer, synthesizes test-only landmarks directly from visible wire
pixels, and generates invented source PNG files. It covers success,
edited observations and frame labels, modified source PNG bytes,
missing source frames, absent operator capture declarations, receipt
overwrite prevention, receipt symlink substitution, mutation during
verification, descriptor-pinned digest reading and symlink rejection,
and stdout/stderr secrecy. It requires no original
PS3 media or private paths in the GitHub repository.
