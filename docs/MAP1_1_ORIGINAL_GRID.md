# First original map format: map1-1 (PS3)

This document records **structure and aggregate measurements only**, not
copyrighted level files or game code. The source is the user-provided
`NPEB00148` package and its verified `cdata.psarc` manifest.

## Real files and measured sizes

| PSARC file | Length | Observed type |
| --- | ---: | --- |
| `data/maps/map1-1.coll` | 141,538 bytes | CSV-like grid with 2,500 records |
| `data/maps/map1-1.vis` | 666,502 bytes | CSV-like visibility data with 2,500 records |
| `data/maps/map1-1.ini` | 23,827 bytes | Object placements and properties |
| `data/script/map1-1.lua` | 119,691 bytes | Readable mission script, 3,402 lines |

The Lua header labels the mission as Chapter 1's tutorial map. Its text is
not committed to GitHub.

## Collision-grid statistics

- Grid size **50 × 50**, coordinates 0–49, exactly 2,500 rows.
- Origin **(-250.0, -250.0)** and horizontal step **(10.0, 10.0)**.
- Four numeric samples and two boolean values are present in each row.
- Numeric samples range from **-8.652534 to 31.000328**.
- **957** cells have at least one nonzero numeric sample.
- **888** cells have non-uniform numeric samples.
- Boolean columns contain **302** and **11** true values, respectively.

Numeric samples could represent geometry heights; boolean fields may express
collision or movement properties. **Those semantics are hypotheses**, not
verified rules of the original engine. Do not use them directly as original
movement costs or passability flags yet.

## VIS and INI evidence

The `.vis` text has a three-line header, announces **2,500** records and
contains exactly that number of following records with variable column counts.
The meaning of those columns is still unverified.

The `.ini` file is section-oriented and contains placed objects and
properties such as base/reference, location, orientation and scale.

## Reproduce safely

The scanner can summarize this map in memory from the **locally held PKG**
without exporting any file contents:

```sh
python3 -m tools.inspect_debug_pkg_assets \
  "/path/to/NPEB00148.pkg.zip.001" "/path/to/NPEB00148.pkg.zip.002" \
  --map map1-1 --json > local-map1-1-summary.json
```

Research code: `tools/inspect_map_coll.py`. Synthetic-only unit tests:
`tests/test_inspect_map_coll.py`.

The report contains counts, numeric ranges and structural metadata. No
copyrighted rows, Lua scripts, images, models, shaders or game executable are
committed to this repository.

## Switch-native next steps

1. Preserve these formats and build a platform-neutral C loader for the
   original 50×50 grid structure, using synthetic test fixtures.
2. Validate the meaning of numeric samples and flags before claiming accurate
   in-game movement, occlusion or collision.
3. Extend the renderer to handle large, variable-size maps.
4. Research DDS-in-`.tga` textures, `.bmodel` geometry, `.banim`
   animations and Lua APIs, each with independent evidence.
5. Test one locally provided real map on Switch hardware.

The present 8×6 Switch grid is **synthetic**; this report does not make it
a port of the original mission.
