# Stage237 — caller-owned movement forecast cache

The asset-free 8×6 isometric Switch research NRO previously recalculated the
entire movement danger matrix during every frame, including hover-only frames
and while the user moved the D-pad cursor. Each cell may perform a route BFS
and one simulated enemy turn, so unchanged tactical state made this redundant.

## Implementation

- `FojBattleThreatCache` lives with the Switch isometric guest. There is
  no singleton, global state, heap allocation or resource-dependent data.
- The cache stores one complete movement threat matrix. Its key contains
  **the complete tactical battle**, except `cursor_x/y`: movement legality,
  damage and enemy destination do not depend on cursor hover.
- On hover-only redraws, the previous forecast is reused while the
  cursor-specific purple landing marker and terrain pointer still re-render.
- HP, ZR guard, attacked flag, hero/enemy positions, terrain,
  turn/outcome, selected state or game reset trigger fresh validation.
  Invalid/nonselected battles do not reuse a previous cached matrix.
- A `NULL` cache retains the exact old calculation path, preserving other
  consumers. The existing `foj_iso_render_battle_options` remains callable.
- The cache is a **presentation optimization**. A, B, X, Y, ZR,
  controller input history and enemy AI continue using their original
  battle state and functions; the cached data never influences combat.

## Regression and CI

`tests/test_battle_threat_cache.c` compares cached versus original forecasts
at every one of the 48 cursor positions. It verifies a single matrix
computation and repeated hits, then separately mutates HP, blocked terrain,
elevation, enemy location, turn number and guard state and checks every
cached forecast byte against the non-cached oracle. It tests invalid/terminal
state output clearing, deterministic A/right/A/Y/reset command replay and
**pixel-for-pixel equality** of cached and non-cached rendered frames with
the overlay on/off and during combat changes.

The research CI runs this new test under strict C11 `-Werror` and UBSan.
Native devkitA64 NRO and NeXium integration checks are expected to run for
the new PR. Those results must be inspected before considering integration.

This change is *not* a claim about original PS3 game rules, source material,
Nintendo Switch retail hardware, or playable original-game content. It
modifies only generated-only tactical prototype code and adds no proprietary
assets.
