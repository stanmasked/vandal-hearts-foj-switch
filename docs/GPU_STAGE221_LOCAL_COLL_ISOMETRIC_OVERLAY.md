# Stage 221 — owner-local raw COLL panel in the isometric battle prototype

This is a research visualization of the user's own optional COLL file, **not**
a reconstruction of the original PS3 mission map, elevation, passability or
Vandal Hearts: Flames of Judgment's combat rules.

## On the Nintendo Switch research NRO

The existing `foj-isometric-research.nro` continues to render the completely
invented 8×6 tactical battlefield, synthetic hero/enemy, HP, guard and next
enemy action forecast. Additionally, when a user supplies a **local-only**
valid COLL file at:

    sdmc:/switch/foj/maps/map1-1.coll

a small 8×6 panel appears at the upper right of the image. It displays
the centered 48 raw records already supported by Stage218. For a 50×50
input, the selected source-cell rectangle is x=21–28, y=22–27.

- **L/R:** cycle between four original numeric columns and two raw boolean
  columns. Numeric panels use a relative grayscale/teal ramp; a constant
  column uses a neutral midpoint. Flags have two contrasting colors.
- **D-pad:** move the same research cursor used for tactical actions; the
  corresponding square in the raw data panel receives an amber border.
- **ZL:** show or hide this diagnostics panel.
- All other gameplay controls remain unchanged; **ZR** still guards.

The colors convey only source values and do not indicate real obstacles,
heights, movement costs, visibility or original engine semantics. No COLL
value is copied into `FojDemo` or `FojBattle`. The invented tactical map
cannot become an original FoJ mission simply by placing a COLL on SD.

The console and isometric research NROs now share one bounded,
local-only file loader in `switch/source/local_coll_window.[ch]`. It
parses at most 1 MiB through the existing validated COLl grammar and keeps
only the centered raw window in memory. The temporary source-byte
buffer and the full parsed grid are explicitly wiped from RAM after
extracting that window. Invalid, missing or undersized
files have no effect: the panel is absent and the synthetic battle still
operates. The loaded bytes are never bundled in NROs, committed to GitHub
or transmitted by a CI workflow.

## Tests

`core/coll_battle_overlay.[ch]` renders raw observation colors into the
destination pixel buffer without changing the source grid or battle state.
It validates the requested channel (0–5), cursor bounds, finite numeric
samples, boolean flags, screen dimensions and stride before drawing.

Generated-only C tests cover panel markers and buffer padding, numeric
versus boolean channels, rejection of invalid/nonfinite inputs, and the
shared file loader with synthetic 8×6 and 50×50 COLL fixtures, including
correct centered coordinates and refusal of files larger than 1 MiB. GitHub Actions runs
strict C11 tests, UBSan, research NRO compilation and the existing
isometric image preview pipeline. The isometric-preview workflow also generates a dedicated
`foj-battle-coll-panel-generated-preview` PNG artifact by composing the
actual portable battle renderer with 48 **invented** raw channel values.
This checks panel integration visibly without accessing owner assets.
All PNG preview artifacts remain synthetic because no real game data is
uploaded to CI.

## Dependencies and limitations

Stage221 depends on Stage220 PR #104; Stage220 in turn depends on Stage219
PR #103. Merge and independently verify earlier stages in order before
retargeting Stage221 to `main`. Console emulator/NRO compilation and host
tests do not prove physical Switch operation, original battle fidelity
or publisher provenance of an owner-local source file.
