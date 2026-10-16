# Seventh Nintendo Switch research NRO: synthetic CPU skeletal skinning

The GitHub Actions devkitA64 build now produces:

**`foj-skinning-research.nro`**

This is the project's first *moving vertex geometry* demonstrator driven
by the portable inverse-bind/weighted-skinning math in
[core/skeletal_skin.c](../core/skeletal_skin.c).

**It does not load or animate any original FoJ actor.** The rendered object
is an invented two-part hinged strip generated entirely from original test
code, not a game model, and no game asset is included in the NRO.

The synthetic setup has a root and a child bone. The child rotates through
an exaggerated sine-wave angle, and the vertices of its attached piece are
deformed by CPU linear blend skinning. The viewer uses the same
[CPU wireframe renderer](../core/obj_wireframe.c) as the standalone mesh
probe, without a game GPU pipeline, texture mapping or depth buffer.

## Controls

| Button | Action |
| --- | --- |
| A | Pause or resume procedural animation |
| B | Reset to bind pose and pause |
| D-pad left/right | Rotate camera around vertical axis |
| D-pad up/down | Tilt camera |
| ZR/ZL | Zoom in/out |
| Plus | Exit |

The red upper-right marker means **synthetic research data only**.

## Automated verification

- Strict C11 host tests: [tests/test_skeletal_skin.c](../tests/test_skeletal_skin.c)
- Native project compilation: [switch/Makefile](../switch/Makefile)
- NRO structure validated in the same GitHub Actions artifact
  `foj-switch-research-nros` as the six earlier diagnostics
- No physical Switch runtime validation yet

## What it does *not* establish

The original FoJ data includes BMODEL rig hierarchies and BANIM bone track
quaternions and positions, and those formats can be structurally decoded.
However, the precise original game engine convention for transforming
poses and inverse bind matrices still needs to be verified. This clean-room
test demonstrates that the proposed math is internally consistent; it
does **not** establish accurate in-game skinning or material animation.

For the original-game hierarchy matching and remaining experimental
requirements, see
[REAL_SKINNING_COMPATIBILITY.md](REAL_SKINNING_COMPATIBILITY.md).
