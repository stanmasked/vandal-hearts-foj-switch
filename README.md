# Vandal Hearts: Flames of Judgment — Nintendo Switch Research & Port

Research project for a **native Nintendo Switch homebrew port** of
*Vandal Hearts: Flames of Judgment* (PlayStation 3 / Xbox 360, 2010).

> **Status: research / native ARM64 smoke-test only — no playable port, PS3
> code translation or original gameplay.** Four independent libnx NROs now
> compile in CI, including original-format map and texture diagnostic viewers;
> none runs the original PS3 game.

## Verified user-provided PS3 package

For the first time, the uploaded 605 MB split archive was read and verified
against the ZIP's internal CRC. The real PKG contains valid PS3 magic,
`NPEB00148` content ID and 21 declared items. Its header is **non-finalized
(0x0000)** rather than retail/finalized; publisher authenticity cannot be
established from an internal ZIP checksum. Full SHA-256 and sanitized metadata
are recorded in [docs/REAL_PKG_NPEB00148.md](docs/REAL_PKG_NPEB00148.md).

**No proprietary assets are stored in this Git repository.** The user's real
COLL map was inspected locally, but the original executable, 3D assets and
engine have not been ported. An explicit opt-in, **local-only** COLL exporter
is available at [tools/export_local_coll.py](tools/export_local_coll.py).

## Original asset discovery (verified 2026-10-16)

The **real** non-finalized PS3 package has now been indexed beyond its header:
21 PKG items, including a 235,982,224-byte `cdata.psarc` and a PS3 SELF
`EBOOT.BIN`. The PSARC manifest contains **3,212 actual resource paths** —
including models, animations, textures, 51 Lua scripts, and map data.

See [real PSARC findings](docs/REAL_PSARC_NPEB00148.md) and
[map1-1's original 50×50 grid measurements](docs/MAP1_1_ORIGINAL_GRID.md).
Our [read-only local PSARC inspector](tools/inspect_debug_pkg_assets.py)
can reproduce the manifest analysis (and optionally `--map map1-1`)
using the user's two split ZIP files **without exporting game assets**.

The original game's 3D engine and logic are not running on Switch yet. The
existing native NRO builds remain independent synthetic probes.

## Original COLL reader and native Switch viewer

The verified `map1-1.coll` has a 50×50 structure with four raw numeric
samples and two flags per cell. [core/coll_grid.c](core/coll_grid.c) parses
this format independently of PS3 using C11; strict validation and
AddressSanitizer/UBSan host tests have passed.

A third native research build, `foj-coll-map-research.nro`, can load a
**user-provided local** COLL at `sdmc:/switch/foj/maps/map1-1.coll` and
display six raw data channels. With no valid file, it displays a conspicuous
synthetic fallback, not copyrighted map content. See
[Switch COLL viewer instructions](docs/COLL_SWITCH_VIEWER.md).

This is **diagnostic visualization only**. Numeric values and boolean columns
do not yet have verified in-game meanings, and the FoJ 3D engine / combat
systems remain unported.

## Original textures decoded and fourth Switch NRO

Five original textures were read directly from the user's `cdata.psarc`
and successfully decoded locally. Two contain BGRA8 data and three contain
DXT1/BC1 DDS blocks, despite the game's `.tga` filenames. See
[verified resource signatures](docs/REAL_RESOURCE_SIGNATURES.md).

A new [portable C DDS decoder](core/dds_texture.c), dedicated generated-data
regression tests, and a fourth native homebrew build
`foj-dds-texture-research.nro` are now present. That viewer loads a
**user-supplied local** DDS-in-TGA resource from
`sdmc:/switch/foj/textures/preview.tga`, with a generated-only fallback.
[See viewer instructions](docs/DDS_SWITCH_VIEWER.md).

**The original FoJ models, skeletons, materials and gameplay are not yet
running on Switch.** Decoding a texture atlas is a necessary step, not a
complete 3D game port.

## Original 3D format header reconnaissance

Initial safe header decoding has been implemented for `.bmodel` and
`.banim`, based on the user's real archive. Among **45 sampled models**,
the opening signature and first shape-name length field matched in every
case. Among **41 sampled animations**, a float32 field is compatible with
clip duration; its interpretation remains provisional. See
[real header findings](docs/REAL_MODEL_ANIM_HEADERS.md).

Use the optional `--header-samples 8` on
[tools/inspect_debug_pkg_assets.py](tools/inspect_debug_pkg_assets.py)
to reproduce a bounded model/animation header summary without writing
the original asset contents to disk. Actual 3D geometry, UVs, skeleton
hierarchies and original scene rendering remain outstanding.

## Immediate goal

1. Confirm the provenance and structural validity of the user's European PS3
   package (expected title ID: `NPEB00148`).
2. Identify its package revision, content ID, metadata ranges, encryption
   boundaries, and file integrity **without bypassing protections**.
3. Inventory game assets and engine technology **only after lawful access to
   accessible game files is established**.
4. Prototype a portable renderer, controller mapping and tactical gameplay
   systems based on verified findings.
5. Bring up Nintendo Switch homebrew builds and automated tests incrementally.

The reference PS3 package is approximately 605 MB. **Do not upload it here.**

## Quick start: local header investigation

Requires Python 3.10+ and no third-party packages.

```sh
python3 tools/inspect_pkg.py "/path/to/Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg" --expected-title-id NPEB00148
python3 tools/inspect_pkg.py "/path/to/game.pkg" --sha256 --json
python3 -m unittest discover -s tests -v
```

To inspect consecutive byte chunks of one ZIP (e.g. `game.pkg.zip.001`,
`game.pkg.zip.002`) **without rejoining or extracting the 605 MB archive**:

```sh
python3 -m tools.inspect_split_pkg "game.pkg.zip.001" "game.pkg.zip.002" \
  --expected-title-id NPEB00148 --sha256 --verify-crc --json > pkg-report.json
```

Read [docs/PKG_INPUT.md](docs/PKG_INPUT.md) for archive-type limitations.
Never publish the game package, license files, executables, keys or assets.

## Structure

- `tools/inspect_pkg.py` — bounded, read-only PKG header/metadata inspector.
- `tools/inspect_split_pkg.py` — stream multipart ZIP + embedded PKG in place.
- `tools/inspect_debug_pkg_assets.py` — read-only debug PKG / PSARC file index.
- `tools/inspect_map_coll.py` — structural original-map metadata inspection.
- `tools/export_local_coll.py` — explicit local-only original COLL export.
- `core/coll_grid.c` — portable C loader for the real-format 50×50 map data.
- `core/coll_view.c` — diagnostic six-channel heatmap on large grids.
- `core/dds_texture.c` — portable DDS BGRA8 + DXT1 decoder.
- `tools/export_local_texture.py` — explicit local-only DDS texture export.
- `tools/inspect_bmodel_banim.py` — provisional original model and animation header probe.
- `switch/source/dds_main.c` — DDS viewer reading local files.
- `tests/` — synthetic test fixtures, no proprietary data.
- `docs/PKG_INPUT.md` — local package preparation and safe validation.
- `docs/PORTING_PLAN.md` — milestones and technical unknowns.
- `docs/LEGAL.md` — clean-repository rules.
- `.github/workflows/ci.yml` — automatic host-side tests.
- `switch/` — four native, data-free libnx diagnostic NRO builds.
- `core/tactical_demo.c` — portable synthetic movement BFS, heights and obstacles.
- `core/isometric_demo.c` — portable synthetic CPU rasterizer for isometric tiles.
- `tools/render_isometric_preview.c` — host preview generator using the same renderer.
- `.github/workflows/isometric-preview.yml` — shareable synthetic PNG render artifact.
- `tools/validate_nro.py` — structural check for compiled NRO output.
- `.github/workflows/switch-nro.yml` — CI build with devkitA64.
- `docs/SWITCH_BRINGUP.md` — build and validation evidence levels.

## Native Switch bring-up

Four independently written research binaries compile through devkitA64 and
pass NRO structure validation in the [latest four-NRO build](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/38921473035):
`foj-switch-research.nro` (ASCII tactics), `foj-isometric-research.nro`
(CPU isometric tactics), `foj-coll-map-research.nro` (COLL viewer), and
`foj-dds-texture-research.nro` (original-format DDS viewer), in artifact
`foj-switch-research-nros` in the updated workflow runs.
The corresponding pixel renderer is also compiled on Ubuntu to generate a
**synthetic screenshot** through the [preview workflow](.github/workflows/isometric-preview.yml).
These are **homebrew graphics/input/logic probes**, not a playable FoJ port.
See [docs/SWITCH_BRINGUP.md](docs/SWITCH_BRINGUP.md).

## Relationship to the PS1 project

The separate [Vandal Hearts PS1 Switch repository](https://github.com/stanmasked/vandal-hearts-switch-remaster)
contains useful devkitPro/libnx, SDL2 and graphics *probes*. Those are not a
port of the PS3 engine. We will selectively **adapt infrastructure**, not
mistake compatibility probes for completed game systems.

## Status / limitations

- PKG content may be encrypted, and the container header alone does not reveal
  models, maps or executable game logic.
- Map COLL and sampled DDS formats are verified; 3D meshes, animations,
  engine implementation and authentic gameplay remain unknown.
- The goal is homebrew development, not an official Nintendo release.
- Compatibility, performance, and game completeness are unknown until tested.

This independent project is not affiliated with or endorsed by Konami,
Sony Interactive Entertainment, Nintendo or the original developers.
