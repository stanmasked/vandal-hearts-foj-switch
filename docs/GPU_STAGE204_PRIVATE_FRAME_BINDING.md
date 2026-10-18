# Stage 204 — bind annotated research poses to actual local native frames

Stages 196–199 compare operator-labelled poses with **no evidence that the
experimental-side coordinates were selected from the viewer's own images**.
Stage 203 already produces nine owner-private, CPU-rendered PPM images
using the **production C** FOJRM001/BANIM parser, player, skinning and
wireframe. Stage 204 adds a fail-closed **research-side annotation-to-frame
evidence gate**.

## What the new gate verifies

`tools/foj_stage204_private_frame_landmarks.py` accepts:

- the original private Stage196 observation JSON (3–9 ordered
  correspondence frames, normalized coordinates, 4–32 point identifiers
  and reported capture times);
- a separate **private frame-binding manifest**;
- the actual owner-private `private-frames/` directory emitted by
  Stage203.

The binding manifest maps each **experimental** observation frame to
**one distinct named local PPM frame** from Stage203. Names must appear in
the exact native-rendered state order:

`initial`, `play_025`, `paused`, `fade_0`,
`fade_025`, `fade_050`, `fade_075`, `fade_done`, `reset`.

For every experimental landmark, the tool checks that an exact-colored
native wire pixel lies no farther than **10 pixels** from the manually
reported normalized location on that *specific* 480 × 320 PPM. It
rejects mislabeled/missing frames, symlinks, truncated or malformed
PPM, invisible wire, duplicate or out-of-order frame associations,
off-wire landmarks, duplicate point IDs or invalid Stage196
annotations.

**The original PS3 landmark locations are not verified by this tool.**
The result means only that the operator's *research-side* marks are
close to visible lines in selected local viewer frames. It does NOT
prove that those marks refer to the correct body parts, that the
original PS3 captures are authentic, that sample times actually
correspond, or that native research skinning matches the PS3 engine.

The PPM wire color is taken from the existing C renderer and is
checked as bytes **in that renderer's existing emitted PPM channel
order**; no automatic image processing or external Python imaging
library is necessary.

## How to use locally

Prepare a Stage196-format observation document whose
`experimental_xy` fields are manually marked on the actual nine
research PPM frames. Independently acquire and annotate the same
visible landmarks in user-authorized original PS3 playback. Do not
copy observations from synthetic fixtures into a claimed original
capture.

Write a **private** manifest in the ignored
`local-data/observations/` folder, for example:

```json
{
  "schema": "foj.stage204.private_frame_binding.v1",
  "frame_labels": ["initial", "play_025", "fade_025"]
}
```

Here each row in your Stage196 JSON corresponds to the same index
in `frame_labels`. For a 480 × 320 image mark normalized
`experimental_xy` as x / 479, y / 319 using the exact native
PPM pixel grid. The private images may contain user-owned protected
silhouettes; keep them **off GitHub and all public cloud services**.

Standalone check:

```sh
python3 -m tools.foj_stage204_private_frame_landmarks \
  --observations local-data/observations/pose-landmarks.json \
  --bindings local-data/observations/native-frame-binding.json \
  --frames-dir local-data/stage203-private-evidence/private-frames \
  > local-data/observations/native-frame-audit-private.json
```

Or run the complete Stage203 workflow **in a new output directory**
with the new optional `--frame-bindings` argument and
`--observations`:

```sh
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --observations local-data/observations/pose-landmarks.json \
  --frame-bindings local-data/observations/native-frame-binding.json \
  --output-root local-data/stage204-private-evidence
```

When present, the Stage203 bundle adds
`private-research-frame-audit.json` with numeric **maximum research
wire distances per frame** and an explicit evidence-boundary warning.
Its summary sets `research_landmarks_bound_to_native_frames=true`
only if **all** marks passed. Without a binding manifest, the field
remains false.

If a bound point does not match, or if the named PPM is missing,
Stage203 fails the entire operation and cleans the **newly created**
private output. Existing owner files/directories are never
overwritten.

## Limits: frame names, timestamps and authenticity

The nine Stage203 state frames include a reset and experimental A→B
crossfade, not a contiguous recording of the actual PS3 title. Their
display order is **not** the source game timebase; the operator must
supply actual independent capture timestamps and not infer real
PS3 scheduler timing from the file names.

The native renderer outputs only wireframe of **experimental research
skinning**. Wire proximity is necessary for the particular
experimental annotations but insufficient for anatomical correctness;
10 pixels is only a deliberately bounded spatial tolerance, not a
PS3 similarity threshold.

Neither this program nor Stage203 automatically finds points in the
original PS3 screenshots. Genuine source comparisons remain
unverified until authorized, privately reviewed source frames are
acquired and annotated with matching actor, clip, camera, and
timing. No original PS3 game asset, source photo or even
asset-derived aggregate report is uploaded to public CI.

## Public CI evidence

`tests/test_foj_stage204_private_frame_landmarks.py` uses entirely
invented wire pixels and invented Stage196 observations. It verifies
acceptance of correctly bound images, rejection of shifted/scrambled
landmark rows, bad frame order, tampered/wrong-channel PPM, symlinks,
absent images, malformed annotation, bad manifest schema and CLI
privacy. Stage203's existing native smoke tests continue to exercise
real production C with synthetic model/animation bytes.

Passing these tests proves only the **research-side frame-binding
verification code**, not the user's authentic PS3 observations.
