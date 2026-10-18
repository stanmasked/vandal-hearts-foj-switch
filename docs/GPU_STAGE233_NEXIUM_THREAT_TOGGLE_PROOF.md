# Stage233 — genuine NeXium proof of a display-only threat toggle

Stage232 lets the player hide or restore synthetic movement danger markers
using a click of the **right stick**. This stage independently verifies
the actual Nintendo Switch research NRO instead of inferring successful
behavior from a native unit test.

## Emulator scenario

Use devkitA64 to build the generated-only isometric NRO, then launch it
in headless NeXium with software Vulkan and capture four real PNG frames:

1. **Initial:** no hero selected, no teal/orange danger marks, no
   controller commands in the replay bar
2. **Press A** (keyboard C): movement risk markers appear, the replay bar
   contains one controller event
3. **Press right-stick click** (keyboard G): risk marks vanish, but
   hero/enemy and recorded input count remain unchanged
4. **Press right-stick click again:** safe/risky hints return at the
   same destination tiles, with no change to gameplay history

The fail-closed screenshot checker verifies the exact 1280×720 guest,
checks both bounded glyph regions from confirmed NeXium capture
calibration, requires constant hero and enemy colors across all frames,
and verifies the replay input meter remains unchanged across both
right-stick clicks. Ten generated-only fixture cases reject wrong,
early, missing or stale markers, a fake toggle, changed units,
unexpected gameplay inputs, blank or wrong-size frames.

## Integration and scope

Stage233 is stacked on Stage232 PR #116, which itself follows Stage231
PR #115. Merge the predecessors only after their complete latest-head
CI passes, then retarget this PR to `main` and require fresh
independent devkitA64, host and real NeXium checks before merging.

This proves only a view toggle in the invented 8×6 homebrew simulation,
not original PS3 gameplay, assets or physical Nintendo Switch execution.
