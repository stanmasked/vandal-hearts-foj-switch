# Vandal Hearts: Flames of Judgment — Nintendo Switch Research & Port

Research project for a **native Nintendo Switch homebrew port** of
*Vandal Hearts: Flames of Judgment* (PlayStation 3 / Xbox 360, 2010).

> **Status: research / native ARM64 smoke-test only — no playable port, PS3
> code translation or original gameplay.** Nine independent libnx NROs now
> compile in CI, including original-data wireframe and DDS-textured actor research viewers;
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

## First authentic PS3 model geometry recovered

**All 583** original FoJ `.bmodel` files were checked: the opening mesh
section in each follows the same verified big-endian vertex/UV/normal/triangle
layout. In total these first sections contain **320,810 triangles**.

A real archery target's first shape (1,167 vertices, 389 triangles) was
rendered locally from the user's model data and converted to OBJ without
committing commercial geometry to GitHub.

See [fully verified model format findings](docs/REAL_BMODEL_FIRST_SHAPE.md),
[local OBJ geometry converter](tools/decode_bmodel_geometry.py) and
[the fifth native Switch viewer](docs/OBJ_SWITCH_VIEWER.md).
The new `foj-obj-wireframe-research.nro` reads a **user-provided**
`sdmc:/switch/foj/models/preview.obj` on Switch, and otherwise
displays an invented test cube.

A recognizable 3D model on desktop is **not yet** a complete original
FoJ scene, textured material pipeline, skinned animation,
nor verified Switch-hardware gameplay.

## Complete original FoJ geometry and material tables (2026-10-16)

**All 583** original `.bmodel` resources now have their full mesh-section
tables structurally decoded: **1,380 shapes and 583,431 triangles**, not
just their first meshes. The optional `0x0F` skin weights have been verified
in **275 sections** from 87 models. These give bone indices and normalized
influence weights, but not skeletal poses.

**895 material-to-texture references** were identified. Of these, 143 names
were ambiguous across directories; each is uniquely resolved by preferring
the texture in the **same directory as the source model**. See the
[full BMODEL research report](docs/REAL_BMODEL_COMPLETE.md).

[Complete-model research tool](tools/inspect_complete_bmodel.py) can export
all original parts into one user-local OBJ with material labels. The
[aggregate audit](tools/audit_all_bmodels.py) checks complete tables without
writing proprietary geometry to disk. An original five-section avatar
(4,722 vertices, 1,574 triangles) has been reconstructed with its local DDS
texture atlas for diagnostic examination.

The existing fifth
[Switch OBJ wireframe viewer](docs/OBJ_SWITCH_VIEWER.md) has been updated
to accept the multi-shape OBJ material labels, but it **still draws only
wireframes**, does not animate the skeleton, and has not been tested on actual
Switch hardware. There is still **no playable FoJ port**.

## Original skeletons and all BANIM motion tracks recovered

In the user-provided PS3 data, **89 BMODEL files** have embedded bone trees
(2,512 bone records). All **450 BANIM animation clips** have been structurally
decoded into **16,631 bone tracks / 1,274,805 keyframes** — including
unit quaternions and translations. Three original environment clips have
zero duration and one key, and are correctly accepted.

See [complete rig/animation evidence](docs/REAL_RIG_BANIM_FORMAT.md),
[Python format decoder](tools/decode_rig_banim.py) and
[native ARM64-compatible C animation core](core/banim_core.c).

A **sixth research NRO**, `foj-banim-research.nro`, can inspect a selected
user-owned BANIM file from Switch SD card, including per-track sampled pose
values. See [BANIM Switch instructions](docs/BANIM_SWITCH_VIEWER.md).
This is still **local-pose inspection**, not bone-matrix skinning, rendered
character animations, original gameplay or verified physical-console operation.

## Skeletal matching and experimental animated-vertex rendering

Every original rig-bearing BMODEL now has at least one BANIM clip with an
identical **full parent hierarchy**: **89/89 models**. Among 450 original
clips, **449** match one or more original model hierarchies. The remaining
`brawler_hammer_smash.banim` has 74 tracks and no exact match.
There are 24 shared hierarchy patterns and 4,011 structural candidate
model/clip pairs. This is an **eligibility filter**, not proof every pairing
is intended by the game. See
[original asset-compatibility audit](docs/REAL_SKINNING_COMPATIBILITY.md).

[core/skeletal_skin.c](core/skeletal_skin.c) now calculates hierarchical
world matrices, rigid inverse-bind palettes and up to five weighted bone
influences per vertex. The resulting **seventh independent Switch NRO**,
`foj-skinning-research.nro`, displays an *invented moving two-bone
wireframe*, reusing exactly that C math. It does not yet draw any authentic
FoJ actor, and physical Switch runtime remains unverified. See
[SKINNING_SWITCH_VIEWER.md](docs/SKINNING_SWITCH_VIEWER.md).

## Original rigged avatar + native animated wireframe input (2026-10-16)

A **private local user-data pair** has now been assembled directly from the
original NPEB00148 PS3 archive: `avatar_body.bmodel` and
`avatar_idle.banim`. The full five-section mesh contains 4,722 vertices
(1,574 triangles), 28 original bones and 14,166 weight influences. The
matching idle clip has 28 parent-compatible tracks and 5,600 keys over
approximately 6.633 seconds.

[tools/export_local_rigmesh.py](tools/export_local_rigmesh.py) converts the
user-owned BMODEL to the new endian-stable `FOJRM001` format; the
[portable C decoder](core/rigmesh_io.c) reads it with strict limits.
[tools/check_local_rig_pair.py](tools/check_local_rig_pair.py) independently
checks bone parents, attribute arrays, weights and animation samples.

The **eighth native NRO**, `foj-rigged-actor-research.nro`, can load
a user-provided `preview.fojrm` plus `preview.banim` from SD and run
experimental weighted CPU skinning on **original** game geometry, showing
a wireframe without any bundled PS3 assets. Compilation and synthetic
regression tests are confirmed; physical Switch launch is not.
[Installation and source file guide](docs/ORIGINAL_RIGGED_ACTOR_SWITCH.md).

An independent local desktop diagnostic calculated original-geometry
poses at 0.0, 3.317 and 6.603 seconds. The vertices remain finite and
change positions, but the mean displacement from static source geometry
was ~6.8 source units; **the original game's exact bind/pose conventions
are not yet confirmed**. This is a milestone toward graphical animation,
not a playable or visually faithful PS3 engine port.

## First original textured actor rendering (2026-10-16)

The project's first independent **filled 3D textured mesh renderer** is now
implemented. [core/textured_triangles.c](core/textured_triangles.c) renders
UV-interpolated triangles with DDS BGRA8/DXT1 atlas sampling, transparent
texel rejection and a depth buffer. Generated C regression tests pass
(including sanitizers).

An original user-supplied FoJ `avatar_body.bmodel` has now been displayed
on the desktop **with its original `avatar_texture.tga` (DDS DXT1,
1024×1024)**, rather than false flat colors. Multiple genuine
`avatar_idle.banim` timestamps have also been rendered using experimental
skeletal deformation, retaining texture UVs. The initial nonflipped V
orientation yields visibly more plausible atlas mapping than a flipped-V
comparison, although original PS3 material fidelity remains unverified.

The **ninth native Switch build**, `foj-textured-actor-research.nro`,
can load the same user-controlled original character mesh + BANIM + DDS
atlas from SD, without embedding commercial files in NRO or GitHub. See
[local setup and limitations](docs/TEXTURED_ACTOR_SWITCH.md).

The program is **CPU rasterized, orthographic, single-atlas and does not
recreate the FoJ game engine**. It has passed ARM64 compilation, but
real-console performance and exact original character animation are not
yet verified. This is not a finished HD remake or playable game.

## Original multi-material DDS support (2026-10-16)

Direct re-audit of all **583 original PS3 BMODEL** resources shows **189**
models with multiple material records, but only **120** with multiple
*distinct* DDS texture basenames. **463** use a single DDS atlas even when
their material flags may differ. Six skeleton-bearing models need at least
two distinct atlases. The maximum observed unique texture count is eight.

The [private material exporter](tools/export_local_material_pack.py)
resolves texture references back to original PSARC paths and writes a local
`FOJMAT01` table plus the exact required DDS files. The [portable
multi-material rasterizer](core/textured_triangles.c) draws all shape
sections into one persistent depth buffer. The **existing ninth Switch
NRO** now optionally loads `preview.fojmat` + `texture_00.tga` etc.,
or continues to use `preview.tga` for one-atlas models.

[Local setup, grounded counts, and remaining limitations](docs/MULTI_MATERIAL_SWITCH.md).
This **does not reproduce** the original material shader properties
(two-sided flags, lighting, blending, filtering), demonstrate Switch GPU
rendering, or establish the actual console frame rate.

## GPU vertex staging from actual original FoJ Daldren geometry

A standalone [portable vertex stream](core/gpu_vertex_stream.c) converts
CPU-skinned original-compatible FoJ XYZ/UV vertices into clip-space
coordinates, and retains ordered per-section DDS binding batches. It was
**compiled and tested locally** under strict C11 and ASan/UBSan.

Using the actual private `cape_daldren_stone.bmodel` sample, all **9,066
vertices** were prepared into **217,584 bytes** of GPU-layout data, with
**six batches across two original DDS atlases**. An aggregate-only report
was produced in conversation, without publishing original asset values.

Basic [vertex and fragment shader sources](gpu/shaders/) and an
[optional ahead-of-time UAM build](gpu/Makefile) have been added.
**They have not yet been compiled into DKSH or run on Switch**: UAM is
not installed in the current local workspace. Native deko3d commands,
swapchain, GPU uploads and actual rendered frames remain work to do.
[GPU staging evidence and next steps](docs/GPU_VERTEX_STAGING.md).

Recent GitHub Actions runs have not exposed even their individual job
steps or logs, so current GitHub CI failures are **not sufficient
evidence of code/test failures**; local C tests are verified separately.

## GPU clip-depth correction and DKSH safety gate

Verified against the original user-local Daldren model, the
[GPU-oriented vertex stream](core/gpu_vertex_stream.c) now maps the
model's camera-space depth range to **[0.01,0.99]**, avoiding rejection
by deko3d's default **0-to-1** clip-depth interval. This preserves
the CPU renderer's closer-is-larger depth order with GPU depth compare
`GREATER` and clear value `0`. Across all **9,066** model vertices,
output remains finite; six shape batches and both original DDS atlas
assignments were unchanged.

The future optional [UAM shader build](gpu/Makefile) now runs a
[DKSH container integrity check](tools/validate_dksh.py), with
synthetic format regression tests. **The DKSH shaders are not compiled
yet** because UAM is absent locally; no deko3d draw calls or physical
Switch GPU frames are claimed.

Latest GitHub Actions runs still report failures **without any job
step logs**, so the locally executed strict C11/ASan/UBSan vertex tests
are the reliable confirmation for this specific change. See
[GPU staging details](docs/GPU_VERTEX_STAGING.md) and
[the CI infrastructure issue](https://github.com/stanmasked/vandal-hearts-foj-switch/issues/15).

## Optional native deko3d GPU clear-and-present probe

The next hardware validation gate now has a **separate, shader-free
deko3d NRO source** at
[gpu/deko3d_clear_main.c](gpu/deko3d_clear_main.c).
It allocates two 1280×720 RGBA8 presentation images, a deko3d command
buffer and graphics queue, submits a color-clear command to the GPU and
presents the result. It contains **only generated colors** and is
isolated from the nine existing CPU/diagnostic NROs.

Build instructions: [gpu/clear.mk](gpu/clear.mk) and
[DEKO3D_GPU_CLEAR_SMOKE.md](docs/DEKO3D_GPU_CLEAR_SMOKE.md).
The independent GitHub Actions
[GPU smoke workflow](.github/workflows/gpu-clear-smoke.yml) was
triggered, but its first run **failed without any job steps or logs**,
like unrelated existing workflows. No GPU NRO build success or actual
Switch frame has yet been established.

This is groundwork for the **first hardware-generated color frame**,
then shader-backed generated triangles, then the user-local original
two-atlas Daldren actor. GPU fidelity/performance remain unknown.

## GPU command-list safety and local host regression (2026-10-16)

The isolated [deko3d clear/present smoke program](gpu/deko3d_clear_main.c)
has been revised against switchbrew's official examples to use
**pre-recorded GPU command lists**, a full-screen scissor and correctly
allocated GPU image memory. It alternates two generated colors across a
double-buffered 1280×720 framebuffer, without including game assets.

The allocation/palette logic is factored into
[gpu/smoke_plan.c](gpu/smoke_plan.c), which passes local strict C11,
ASan and UBSan tests. Developers can reproduce this without a Switch
SDK using `make -f gpu/clear.mk host-check`.

The **native deko3d NRO remains unverified**: [optional GitHub Actions
attempt #38950129942](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/38950129942)
again failed at job startup with zero steps, as did unrelated Python
tests. Neither Switch compilation nor actual GPU display is confirmed.
[Details and acceptance tests](docs/DEKO3D_GPU_CLEAR_SMOKE.md).

## Executable deko3d command-flow verification without hardware

To test the first GPU app while GitHub Actions runner startup remains
unavailable, [tests/test_deko3d_clear_host.c](tests/test_deko3d_clear_host.c)
now **executes the real source of our isolated
[gpu/deko3d_clear_main.c](gpu/deko3d_clear_main.c)** against a small
stateful, host-only deko3d/libnx API mock. It checks swapchain slot
selection, four pre-recorded GPU command lists, two color modes,
present sequencing and cleanup.

**Locally tested: 242 simulated frames, nine injected failure paths,
zero remaining allocations in all scenarios**, with strict C11 and
ASan/UBSan. Run `make -f gpu/clear.mk host-check` and
`make -f gpu/clear.mk host-mock-sanitized` without devkitPro.
Full [engineering record](docs/DEKO3D_GPU_CLEAR_SMOKE.md).

These are software mock results. **No real deko3d shader compilation,
native GPU NRO cross-build or frame presented on physical Switch** is
claimed; GitHub Actions is still failing before creating job steps.

## GPU smoke-test: full host API lifecycle exercised

The optional deko3d program now has a
[stateful mock driver test](tests/test_deko3d_clear_host.c) that
**compiles and executes the actual native GPU smoke entrypoint** on
desktop, with compact [host-only deko3d/libnx headers](tests/mock_switch_sdk/).
Unlike the original math-only test, it checks **242 acquire/submit/present
cycles**, four framebuffer/color command lists, nine injected failures,
and a Plus-button exit after two frames. All eleven paths release their
mock resources, and local strict C11 and ASan/UBSan runs pass.

Run `make -f gpu/clear.mk host-check` or
`make -f gpu/clear.mk host-mock-sanitized` without devkitPro.
[Setup and evidence](docs/DEKO3D_GPU_CLEAR_SMOKE.md).

**A simulated GPU is not a physical GPU.** No cross-compiled deko3d NRO
or Switch presentation was verified: current GitHub-hosted jobs continue
to fail before recording any executable steps.

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

The source PS3 package is approximately 605 MB; keep game assets out of GitHub.

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
- `tools/decode_bmodel_geometry.py` — verified first-shape model decoder and local OBJ export.
- `tools/inspect_complete_bmodel.py` — full 1–50 shape decoder and local OBJ export.
- `tools/audit_all_bmodels.py` — aggregate audit of meshes, skinning and texture references.
- `tools/decode_rig_banim.py` — original BMODEL bone records and BANIM tracks.
- `tools/audit_rig_anims.py` — local-only aggregate 583-model / 450-clip validation.
- `tools/export_local_banim.py` — one explicit user-owned BANIM export.
- `core/banim_core.c` — portable native BANIM parser and pose sampler.
- `core/skeletal_skin.c` — inverse-bind hierarchy, experimental CPU weighted skinning.
- `core/rigmesh_io.c` — bounded private FOJRM001 native mesh/bone/weight reader.
- `tools/export_local_rigmesh.py` — local original BMODEL to FOJRM001 conversion.
- `tools/check_local_rig_pair.py` — local rigged mesh and animation compatibility audit.
- `core/textured_triangles.c` — portable multi-atlas textured triangles sharing one z-buffer.
- `core/material_table.c` — bounded FOJMAT01 per-shape material slot reader.
- `tools/export_local_material_pack.py` — opt-in per-model original DDS mapping and private local export.
- `switch/source/textured_actor_main.c` — ninth real-data-capable CPU textured character viewer.
- `tools/audit_rig_clip_pairs.py` — original-game bone-hierarchy pairing audit.
- `core/obj_wireframe.c` — native-compatible OBJ diagnostic renderer.
- `switch/source/dds_main.c` — DDS viewer reading local files.
- `tests/` — synthetic test fixtures, no proprietary data.
- `docs/PKG_INPUT.md` — local package preparation and safe validation.
- `docs/PORTING_PLAN.md` — milestones and technical unknowns.
- `docs/LEGAL.md` — clean-repository rules.
- `.github/workflows/ci.yml` — automatic host-side tests.
- `switch/` — nine native libnx research NROs; original-data-capable builds contain no bundled game assets.
- `core/tactical_demo.c` — portable synthetic movement BFS, heights and obstacles.
- `core/isometric_demo.c` — portable synthetic CPU rasterizer for isometric tiles.
- `tools/render_isometric_preview.c` — host preview generator using the same renderer.
- `.github/workflows/isometric-preview.yml` — shareable synthetic PNG render artifact.
- `tools/validate_nro.py` — structural check for compiled NRO output.
- `.github/workflows/switch-nro.yml` — CI build with devkitA64.
- `docs/SWITCH_BRINGUP.md` — build and validation evidence levels.

## Native Switch bring-up

Nine independent research binaries compile through devkitA64 and
pass NRO structure validation in the [ninth-NRO build](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/38938041742):
`foj-switch-research.nro` (ASCII tactics), `foj-isometric-research.nro`
(CPU isometric tactics), `foj-coll-map-research.nro` (COLL viewer), and
`foj-dds-texture-research.nro` (DDS viewer), and
`foj-obj-wireframe-research.nro` (user-local mesh wireframe), and
`foj-banim-research.nro` (user-local bone-track timeline), and
`foj-skinning-research.nro` (generated two-bone wireframe), and
`foj-rigged-actor-research.nro` (user-original avatar/clip wireframe), and
`foj-textured-actor-research.nro` (user-original avatar/clip/DDS CPU raster), in artifact
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
- COLL, DDS, BMODEL mesh/rig and BANIM keyframe formats are structurally
  identified. Experimental CPU skinning math is implemented, but original
  engine skinning/blending, gameplay and campaign remain unimplemented.
- The goal is homebrew development, not an official Nintendo release.
- Compatibility, performance, and game completeness are unknown until tested.

This independent project is not affiliated with or endorsed by Konami,
Sony Interactive Entertainment, Nintendo or the original developers.
