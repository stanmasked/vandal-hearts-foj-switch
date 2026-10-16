# Native DDS texture viewer (research build)

FoJ PS3 textures may have a `.tga` filename but a real **DDS** file
header. Five user-owned original assets have been decoded successfully in
the local analysis environment: **two BGRA8 and three DXT1**. The C11 decoder
in `core/dds_texture.c` supports these two legacy DDS formats, producing
libnx-compatible RGBA8888 pixels. Formats beyond these two are rejected.

## Fourth Nintendo Switch NRO

The `devkitA64/libnx` build produces:

`build/foj-dds-texture-research.nro`

It tries to load a user-controlled texture file from:

`sdmc:/switch/foj/textures/preview.tga`

The `.tga` suffix intentionally matches the original game; the file itself
must begin with `DDS ` magic. It can contain either a DXT1 texture or
uncompressed BGRA8, with an ordinary legacy DDS header.

If the file is absent or unsupported, the NRO displays a **synthetic 8×8
generated DDS gradient**. A red upper-right marker means fallback; a green
marker means some structurally valid local texture was decoded. Green is not
publisher authentication.

## Controller bindings

| Button | Action |
| --- | --- |
| D-pad | Pan image |
| ZR | Zoom ×2, up to ×8 |
| ZL | Zoom ÷2 |
| Plus | Exit |

The viewer fits the texture into a 1280×720 framebuffer at default zoom and
draws transparent texels against a checkerboard. It does not render any
original 3D model, material, animations or FoJ in-game geometry.

## Optionally prepare one texture locally

If you own and are allowed to inspect the original PS3 data, run from the
repository root with the **two local split ZIP parts**:

```sh
mkdir -p local-data/textures
python3 -m tools.export_local_texture \
  "/path/to/Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.001" \
  "/path/to/Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/avatar_texture.tga" \
  --output "local-data/textures/preview.tga"
```

The tool explicitly requires an output path, validates that the selected
resource is BGRA8 or DXT1, and refuses to overwrite existing files. It
extracts **only one requested original texture** into your local ignored
directory; it never uploads anything.

On the user's own Switch SD card, place the locally prepared file at:

`/switch/foj/textures/preview.tga`

Then use the NRO. To compare against another source file, replace or rename
the local SD-card preview manually.

**Never commit commercial texture bytes, encrypted archives, EBOOT.BIN or
any game assets to GitHub**. Only the open C decoder, generated fixture tests
and research documentation are stored in the repository.

## Verification and remaining limits

- BGRA8 masks: R=`00ff0000`, G=`0000ff00`, B=`000000ff`,
  A=`ff000000`.
- DXT1: 4×4 block decompression, both four-color and one-bit transparency
  modes, including non-multiple-of-four dimensions.
- Unit tests validate output pixel ordering, buffer stride, bounds,
  truncated inputs and unsupported header variants.
- Native ARM64 build generates a fourth NRO and checks its structural
  metadata in CI.
- Five actual textures were decoded and visually inspected locally using
  an independent DDS-capable decoder; **the C decoder has been tested in CI
  with synthetic fixtures**.
- Real Switch hardware operation, texture display in the original game
  engine, filtering and material UV mapping are **not yet verified**.

Next critical reverse-engineering tasks are `.bmodel` vertex streams and
`.banim` skeleton/pose data so these original textures can be applied to
actual game meshes.
