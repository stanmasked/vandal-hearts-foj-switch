# Stage 230 — actual enemy-turn danger preview for every reachable cell

This feature helps plan movements in the **invented 8×6 tactical battle**.
It is not a reconstruction of Vandal Hearts: Flames of Judgment's PS3 AI,
terrain, enemy ranges or combat rules.

## Gameplay

Press **A** to select the hero. In the isometric research NRO, each
reachable destination now receives a small indicator:

- **Teal:** ending the turn after moving to this cell would cause
  no damage from the existing synthetic enemy.
- **Orange ticks:** expected HP damage (one tick per invented HP,
  up to four ticks). When guarding was already used, the preview
  reflects the lower defended damage.

Move the D-pad cursor over an available cell in the console NRO to see
its exact predicted incoming damage. Invalid, blocked, occupied,
out-of-range and current-hero cells have no marker. The indicators
disappear when selection is cancelled, movement is already committed
or battle ends.

## Technical guarantee

`foj_battle_preview_movement_threat` invokes the **existing route
preview** for each of the 48 cells. For every legal destination it
temporarily relocates the hero on a stack-local `FojBattle` copy,
calls the real `foj_battle_end_turn`, and collects the resulting
hero HP and enemy coordinates. It never modifies the live battle,
commits a move, consumes actions, or reads a COLL diagnostic channel.
The same invented enemy BFS, terrain-height steps, guard effect and
defeat logic are used for previews and actual turns.

Three new portable C battle tests verify all 48 cells against the
real enemy-turn routine, guard and one-HP lethal boundaries, and
rejection of invalid/terminal input. A renderer regression checks
safe/risky exact marker colors, source-state non-mutation and cleanup
on B deselection.

Stage229 PR #113 passed all 13 workflows and merged into `main`
at commit `353ec64f2495f7f851bac2f868a4da6c01f56caf`. Stage230
now targets `main` and requires a new independent CI matrix covering
devkitA64, strict C11/UBSan, rendering, and guest NeXium checks before
the feature can be merged.

No proprietary PS3 assets, map file bytes or game software are included.
