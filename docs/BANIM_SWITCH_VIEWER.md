# Sixth Nintendo Switch research app: FoJ BANIM local pose inspector

The devkitA64/libnx CI now builds **`foj-banim-research.nro`** alongside
the previous five standalone test applications. This program can inspect
**one user-owned original BANIM file** using the same portable native C
parser linked into the NRO.

It displays time, track count, a selected track's parent index, quaternion
XYZW and local translation XYZ. It is **not** the original FoJ animation
system, 3D renderer or playable game.

## Local file

By default the app reads:

`sdmc:/switch/foj/anims/preview.banim`

With no valid file, it uses a **synthetic, generated one-track/one-key clip**
and prominently marks its source as `SYNTHETIC FALLBACK`.

To privately prepare a real example from a user-owned PS3 archive:

```sh
mkdir -p local-data/anims
python3 -m tools.export_local_banim \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/anims/altyria_enrage.banim" \
  --output "local-data/anims/preview.banim"
```

The export is opt-in, requires an explicit path, checks the full BANIM
structure and refuses to overwrite an existing file. **Never upload** the
original game asset, package, licenses or EBOOT to GitHub.

Place `preview.banim` at `/switch/foj/anims/preview.banim` on the Switch SD
card and launch `foj-banim-research.nro`.

## Controls

| Button | Action |
| --- | --- |
| A | Toggle timeline play/pause |
| B | Stop and reset time |
| D-pad left/right | Step backward/forward by 1/30 second |
| D-pad up/down | Select a bone track |
| Plus | Exit homebrew |

The viewer samples the clip's **local track-space transforms**. It does not
build skeletal global matrices, draw original mesh geometry, associate a
clip with a model or apply weighted skinning.

## Engineering evidence and limitations

- Native [BANIM core](../core/banim_core.c) uses bounded parsing, array
  checks and platform-neutral little-endian decoding.
- Keyframes are interpolated using independent research SLERP + linear
  translation.
- [Generated host tests](../tests/test_banim_core.c) validate parsing,
  clamped time, quaternion rotation, zero-duration and malformed clips.
- The GitHub Actions native build links `banim_core.c` against libnx and
  verifies the NRO header and segment bounds.
- **No runtime launch on a physical Nintendo Switch has been verified yet.**

Format evidence for all 450 original game animation clips is in
[REAL_RIG_BANIM_FORMAT.md](REAL_RIG_BANIM_FORMAT.md).
