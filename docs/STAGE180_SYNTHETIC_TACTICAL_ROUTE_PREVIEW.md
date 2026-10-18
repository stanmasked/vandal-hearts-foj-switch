# Stage 180 — synthetic tactical shortest-move route preview

This is an **invented, asset-free tactical prototype** for the
independent isometric Nintendo Switch research NRO. It is **not** a
reproduction of *Vandal Hearts: Flames of Judgment* combat rules,
animations, map assets or AI.

## What changed

The existing 8×6 generated height-map already supported an A-selected
hero, a move budget of four grid steps, blocked cells, one-step height
climbs, and an impassable enemy tile. It highlighted every reachable
destination, but did not show the exact movement route for the
currently highlighted target.

The portable C function `foj_demo_preview_route()` reconstructs a
bounded shortest route using the existing distance field:

- Returns no route for blocked, occupied, out-of-range, unchanged or
  over-budget destinations.
- Includes the hero's starting tile and the destination.
- Uses a stable north/east/south/west backtracking tie order.
- Returns at most five cells, needs no heap, never changes game state.
- Rejects height differences outside ±1 per step.

The existing `foj_iso_render()` CPU rasterizer now draws small **gold
route markers** after the terrain is painted, so later tiles cannot
overdraw them. Press A to select the hero, move the cursor with the
D-pad to a reachable destination, then press A to confirm. Press B to
cancel; the route preview disappears.

## Verification

Portable host tests:

    cc -std=c11 -Wall -Wextra -Werror -pedantic -Icore \
      tests/test_tactical_demo.c core/tactical_demo.c -o /tmp/foj_tactics
    /tmp/foj_tactics

    cc -std=c11 -Wall -Wextra -Werror -pedantic -Icore \
      tests/test_isometric_demo.c core/isometric_demo.c \
      core/tactical_demo.c -o /tmp/foj_isometric
    /tmp/foj_isometric

The tests assert ramp traversal, stable tie-breaking, illegal moves,
route capacity and actual highlighted framebuffer pixels. The normal
research CI compiles both tests. SDK-linked NRO compilation remains a
separate check and does **not** prove runtime framerate or physical
console display.

## Status and limitations

All geometry and rules in this demonstration are independently
invented. No commercial PlayStation 3 executable or game assets
are included. The new route is only a selection preview; it does not
animate movement, spend action points, perform attacks, drive enemy
turns or implement the original FoJ tactical combat system.
