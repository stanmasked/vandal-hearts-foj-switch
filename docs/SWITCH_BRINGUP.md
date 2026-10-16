# Nintendo Switch homebrew bring-up

This phase verifies **compiler/toolchain integration and synthetic tactical
logic plus renderer demonstrators**, using no game files. The NRO is **not**
the PS3 game.

## Build

Requires a recent devkitPro devkitA64 / libnx toolchain and the usual Switch
Homebrew SDK support.

From the repository root:

```sh
make -f switch/Makefile verify
```


Produces two independent, asset-free binaries and checks NRO0 magic,
declared file size, and segment bounds:

- `build/foj-switch-research.nro` — text-console map, controls, and logic.
- `build/foj-isometric-research.nro` — 1280×720 CPU-rendered isometric tiles
  displayed through libnx's linear framebuffer.

GitHub Actions uses `devkitpro/devkita64:latest` to compile the
research NROs and uploads them in artifact `foj-switch-research-nros`.
See [Switch NRO workflow](../.github/workflows/switch-nro.yml).

## Shared controls

- D-pad: move a cursor across the invented 8×6 battlefield.
- A: select the hero at H, or attempt a reachable move.
- B: cancel a selection.
- Plus: exits to the homebrew loader.

The invented elevation- and obstacle-aware movement uses `core/tactical_demo.c`.
A breadth-first search computes reachable tiles with a four-step budget and
maximum one-level climb per step. This is **not** the original game's battle
rules, meshes, renderer, menus, save system, PS3 executable or data.

## Portable movement core

Host-side tests in `tests/test_tactical_demo.c` validate reachability, slope
limits, blocking, selection, rejection, cancellation and cursor clamping.
They are executed through `.github/workflows/ci.yml` with the system C compiler.
The same core source is linked into both Switch `NRO` binaries.

The isometric NRO additionally uses `core/isometric_demo.c` to draw
**synthetic tile diamonds, height extrusions and unit markers** with a portable
CPU rasterizer. Host tests cover projection and pixel-buffer bounds. This is
not FoJ's original 3D rendering engine, does not load real game geometry or
textures, and has not yet been visually validated on real Switch hardware.

## Evidence ladder

1. Successful host-side unit tests — parser and validation only.
2. Successful NRO compiler/linker run — shell builds for ARM64.
3. NRO0 header/segment validation — structural plausibility only.
4. Emulator launch and input smoke test — runtime evidence on emulator.
5. Physical Switch run — hardware compatibility evidence.
6. Original FoJ game asset/render/gameplay tests — true porting progress.

Only claim levels that were specifically measured. Neither the build nor
the NRO metadata validator proves proper runtime behavior.

## Security and distribution

No downloaded game, game patches, PSN entitlements, cryptographic material or
copyrighted commercial assets are ever included in this CI workflow. Keep
original game files local.

## Synthetic host reference image

`tools/render_isometric_preview.c` produces an RGB PPM from the **same**
portable rasterizer as the Switch NRO; `tools/ppm_to_png.py` packages that image
as PNG without third-party Python packages. GitHub Actions workflow
[`isometric-preview.yml`](../.github/workflows/isometric-preview.yml)
uploads artifact `foj-isometric-synthetic-preview`.

The PNG shows invented geometry and units, **not actual FoJ graphics**.
Compare this reference to a later real Switch capture to detect rendering
issues; passing its host pipeline is not proof the NRO was run on hardware.
