# Native Switch COLL map viewer (Gate 1 / early Gate 2)

The observed original map1-1.coll contains **50×50** grid cells, four numeric
samples and two boolean fields each. The exact in-game semantics of these
fields remain unverified.

This stage adds a portable C loader and a third native Switch NRO to display
the six channels as a **diagnostic 2D heatmap**. It is not the original game's
3D map renderer or battle engine.

## Three independently compiled Switch programs

- **foj-switch-research.nro** — synthetic ASCII tactics test.
- **foj-isometric-research.nro** — synthetic isometric software demo.
- **foj-coll-map-research.nro** — COLL real-format diagnostic viewer.

The third NRO looks for the user-supplied local file at:

`sdmc:/switch/foj/maps/map1-1.coll`

If missing or structurally invalid, it instead displays a generated
50×50 test grid. No game assets are embedded into the NRO.

The status rectangle in the upper-right corner is **red** for synthetic data
and **green** for any user-supplied COLL that passed structural validation.
Green is not proof of publisher authenticity.

## Controls

| Button | Function |
| --- | --- |
| D-pad | Move grid cursor |
| R / L | Change among six source-data channels |
| ZR / ZL | Zoom in / out |
| Plus | Exit homebrew |

Channels 0–3 show individual raw numeric columns, normalized from blue to
yellow. Channels 4–5 show the two raw boolean columns (red = true).
Do not interpret these channels as authentic movement or collision rules yet.

## Locally prepare a map from your own PS3 archive

From the repository root, using only your own locally held split ZIP:

```sh
mkdir -p local-data/maps
python3 -m tools.export_local_coll \
  "/path/to/Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.001" \
  "/path/to/Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.002" \
  --map map1-1 --output local-data/maps/map1-1.coll
```

The export is **explicit opt-in**. Only the single requested COLL resource
is written, and the tool refuses to overwrite an existing file. The
local-data directory is excluded via .gitignore.

Copy your own COLL to the SD card path /switch/foj/maps/map1-1.coll.
Never commit the COLL, original package, executable, licenses or decrypted
commercial resources to the source repository.

## Evidence levels

- Portable COLL parser in core/coll_grid.c and heatmap in core/coll_view.c.
- Synthetic parser tests for real-size 50×50 grids and malformed data.
- Synthetic heatmap tests for stride, clipping, channels and cursor.
- CI compiles the ARM64 NRO and validates its container layout.
- **Physical Switch launch, actual map display and game compatibility are
  not yet verified.**

This is a structural visualization diagnostic, not a finished game port.
