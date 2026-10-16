# Original model and animation header reconnaissance

Research conducted on **user-provided** NPEB00148 PKG → cdata.psarc;
none of the original resources is committed to this Git repository.

This is **header reconnaissance**, not full mesh or animation decoding.

## Actual archive inventory

- **583** file paths ending in `.bmodel`.
- **450** file paths ending in `.banim`.

The two formats were sampled at regular intervals through their respective
manifest lists, without redistributing model geometry or animation tracks.

## .bmodel: 45 independent files sampled

**45 / 45** sampled files share an initial recognizable structure:

| Byte position | Observed field | Status |
| --- | --- | --- |
| 0 | `0x0B` | Repeated file-type marker |
| 1 | `0x09` | Repeated header marker |
| 2 | `0x00` | Repeated byte |
| 3 | Small positive integer | **Candidate part/shape count**, unproven |
| 4–6 | `0x01 0x20 0x00` | Repeated marker sequence |
| 7 | Length of first named shape | Confirmed to match following text length |
| 8 onward | First shape identifier | Printable name; observed in every sample |

Examples of first shape identifiers observed include `banditShape_0`,
`avatar_headShape_0` and `archery_targetShape_0`.

The candidate part count often correlates with the number of anatomical or
material sections suggested by the model name, but we have **not yet
reconstructed the per-shape record table, vertex arrays, faces, skinning or
UV coordinates**. The small integer is deliberately not described as
confirmed mesh count in the decoder API.

## .banim: 41 independent files sampled

**41 / 41** sampled files begin with marker `0x0D`, followed by a finite,
positive IEEE-754 **little-endian float32** at bytes 1–4.

The 41 measured values range from approximately **0.033333 to 14.2
seconds**, plausibly animation clip lengths (e.g., brief deflection, long
kneeling-loop animation), but actual time-base interpretation has not yet
been confirmed by running the original game.

Byte 5 varies among at least 12 values in these samples, so it is **not a
fixed format/version signature**. It may encode number of tracks, object
relationships or another field; this requires further study.

No joint hierarchy, quaternion stream, pose timestamps, interpolation, or
actual animation frame data is decoded by this research tool.

## Repeatable, limited inspection

Pure Python module:
[tools/inspect_bmodel_banim.py](../tools/inspect_bmodel_banim.py).

The existing split-PKG/PSARC inspector can optionally sample a limited
number of each format and emit only safe first-name / timing summaries:

```sh
python3 -m tools.inspect_debug_pkg_assets \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --header-samples 8 --json > local-3d-header-report.json
```

Limit is 0–16 samples **per extension**, disabled by default. The report
does not contain original vertex/face/animation bytes. The first shape name
and related filenames *do* come from the original game and should be
reviewed before sharing.

Synthetic, generated-data tests cover both header variants and rejection
of malformed inputs. Real assets were inspected separately in a local
environment and are not CI test fixtures.

## Next milestone

Derive shape record boundaries, mesh counts, vertex positions, index buffers,
material references and UV coordinates, then independently identify the
animation skeleton hierarchy and pose data. Only after that will we be able
to map decoded DDS atlases onto real game models in the Switch renderer.
