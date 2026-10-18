# Stage 205 — private original-game PNG capture binding

Stage 204 confirmed that experimental landmarks touch **specific frames**
of the research C wireframe renderer. The source-game side was still an
unverified set of manually entered coordinates with no binding to actual
image files. Stage 205 closes that **local file-integrity gap** by
requiring the original-side observations to match the *exact content*,
dimensions, and declared timestamps of local owner-held PNG captures.

This is **not** authentication that the screenshots came from original
PS3 hardware or Vandal Hearts: Flames of Judgment. No PS3 game footage
or assets were available to public CI.

## Preparing original-side frames (offline, owner only)

Capture or privately extract **3–12 genuine PNG screenshots** from
authorized original-game playback. Every frame must be in a
noninterlaced PNG with 8-bit RGB or RGBA pixels, at most 4096 px per
dimension and at most 8 million pixels. No external image service,
network requests, or user uploads are performed by this program.

Save captures inside a private Git-ignored local directory, using
strict chronological filenames:

```text
local-data/observations/ps3-frames/
  frame_000.png
  frame_001.png
  frame_002.png
  ...
```

Your separate, owner-private Stage196 JSON contains matching ordered
`ps3_time_seconds` and manual `ps3_xy` landmark annotations, as
well as the experimental `experimental_xy` annotations. Times should
be measured independently from source capture/playback; do not
infer original-engine timing from research filename order or the NRO
state labels.

First create a private content manifest using **the actual image bytes**:

```sh
python3 -m tools.foj_stage205_private_source_png \
  --prepare \
  --observations local-data/observations/pose-landmarks.json \
  --capture-dir local-data/observations/ps3-frames \
  --manifest local-data/observations/source-png-private.json
```

The manifest stores each image's private SHA-256, dimension and declared
source timestamp. It is owner-only and **must never be committed,
uploaded, or attached to a public CI artifact**. The tool refuses to
overwrite an existing manifest.

Verify the same observation data against all source frames later:

```sh
python3 -m tools.foj_stage205_private_source_png \
  --verify \
  --observations local-data/observations/pose-landmarks.json \
  --capture-dir local-data/observations/ps3-frames \
  --manifest local-data/observations/source-png-private.json
```

The checker validates CRCs for all PNG chunks, unique 8-bit IHDR,
contiguous IDAT blocks, a valid noninterlaced RGB/RGBA zlib stream,
bounded decompression, correct filter bytes and exactly one IEND with
no appended data. It rejects missing or symlinked files, mismatched
bytes/width/height, wrong frame order/times, duplicate image hashes,
corrupted PNG, malformed JSON, incompatible manual landmark sets, and
unexpected manifest fields. It never prints original image bytes,
source file paths, SHA-256, or manual coordinates.

Identical byte-for-byte PNGs at different operator timestamps cannot
serve as **distinct** frame evidence for this strict workflow; they
are rejected even though a genuinely static scene could legitimately
look identical. This is a conservative evidence gate, not a claim that
the original game must always move between frames.

## Combined private comparison with Stage203 / Stage204

The Stage203 owner-private pipeline supports two new matching flags,
both required when this source binding is used:

```sh
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --observations local-data/observations/pose-landmarks.json \
  --frame-bindings local-data/observations/native-frame-binding.json \
  --source-png-dir local-data/observations/ps3-frames \
  --source-png-manifest local-data/observations/source-png-private.json \
  --output-root local-data/stage205-private-evidence
```

This combines:

- independent source-side **PNG bytes, time and dimensions** checked
  against a local private manifest (Stage205);
- experimental-side manually chosen points checked against **actual
  rendered C wireframe PPM pixels** (Stage204);
- Stage196's normalized 2D shape comparison, optional Stage197–199 lag
  checks, and Stage203 native playback / private pose envelope.

The source PNG binding is checked **before** creating the new evidence
directory and again after the C renderer runs. Changed/missing PNG
bytes cause the run to fail and the **newly created, incomplete**
private output to be cleared. Existing owner files are never
overwritten. Successful output includes
`private-source-png-audit.json` with counts and explicit false
original-authenticity flags. The private manifest and original images
are **not copied into the evidence bundle**.

The `--frame-bindings` flag is optional and independent. To make a
meaningful two-sided comparison, supply both the Stage204 experimental
binding and Stage205 source PNG binding with *manually reviewed*
landmarks corresponding to the same character pose, camera setup and
action.

## Evidence boundaries

A matching SHA-256 proves only that the local PNG **content** is the
same as when the private manifest was created. It cannot prove the
images were captured from a PS3, which game or animation is depicted,
that manual timestamps are correct, or that the anatomical landmarks
match those on the research wireframe.

Similarly, an experimental point within Stage204's 10-pixel radius of
a wire line is **not** proof of correct skeletal identities or camera
projection. The 2D similarity residual cannot establish correct hidden
bones, bind transforms, animation blending or original game logic.

Every source-authenticity/animation-fidelity flag stays **false**.
The next genuine evidence gate is independently reviewed, authorized
original-game captures and confirmation of character, clip and
timestamp correspondences, performed **privately**.

## Public regression evidence

`tests/test_foj_stage205_private_source_png.py` creates entirely
invented RGB/RGBA images with Python's standard library, and invented
Stage196 landmarks. It checks valid/invalid PNG structure, CRC,
tampering, swapped/identical frames, timestamps, dimensions, symlinks,
no-overwrite, owner-only manifest permissions, protected CLI output,
and Stage203 native C evidence integration.

No commercial PS3 images, real game-derived animation data or source
manifest hashes are present in the repository or Actions artifacts.
