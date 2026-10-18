# Stage225 — cancel an uncommitted movement in invented battle

This is a **quality-of-play improvement for the generated 8×6 tactical
prototype**. No rules or assets are extracted from the PS3 game.

## Control flow

**B** now has two sensible contexts:

- If the hero is selected for a move, B deselects it (unchanged).
- After successfully moving, but **before attacking, guarding (ZR), or
  ending the turn (Y)**, B restores the immediately previous hero
  coordinates and cursor position, and returns the movement action budget.
  The hero can then choose a different route within the same turn.

There is one movement per turn, so only one move snapshot is retained.
Undo never rolls back an attack, guard, damage, enemy action or a completed
turn. An invalid previous position, occupied or blocked cell, terminal
battle, attack/guard already committed, or missing movement all fail or
return no-op without corrupting current state.

The isometric game shows a small mint-green marker beside the hero when
B undo remains available. The console shows the same control in the help
line and displays “Hero move undone” after a successful B action.

The existing Y enemy-action forecast automatically recalculates after
restoring the hero's actual coordinates; the X attack forecast remains
unchanged and authoritative. Neither the optional COLL diagnostics nor
any alleged original PS3 terrain interpretation affects undo.

## Generated-only validation

Four new portable battle regression scenarios cover movement and
selection cancellation, choosing another route after undo, refusing
undo after guard/attack or finished battle, refusing invalid snapshots,
and restoring exactly the baseline forecast. One isometric screenshot
regression checks marker appearance and disappearance on B.

Inherited strict C11, UBSan, Python and research Switch NRO workflows
cover these changes. No original game assets, keys or user-supplied
private maps are checked into GitHub.

Stage224 PR #108 passed Python 3.11/3.13, guest NeXium ZR protection
and inherited COLL checks; it merged into `main` as `444cde1147665c002a8818590660aa1c671583a9`.
Stage225 now targets `main` and requires independent C/Python 3.11/3.13,
NRO, generated renderer and emulator CI before merging. This is still invented
synthetic combat, not a completed port.
