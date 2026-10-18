# Stage234 — cursor-specific next enemy landing preview

This stage extends the **invented 8×6 homebrew** movement-risk UI
with a preview of where the enemy will be after the player's chosen
move and subsequent Y end-turn. The data already exists in
`FojBattleThreatPreview.enemy_{x,y}_after`; no new enemy AI is
introduced, and no original PS3 gameplay is inferred.

## Controls and rendering

While the player selects the hero with A, moving the cursor to a
*legal* destination causes a small **purple 6×6 tab** to appear above
the enemy's predicted post-turn cell. The safe and orange damage
markers continue to show the same predicted HP consequences.

In the console research NRO, the existing destination-risk line
additionally prints the projected enemy coordinates.

The purple marker is absent if a cell is blocked, occupied, unreachable
or the player's current cell; if the player cancels selection with B;
or if right-stick threat-display hiding is enabled. The display
uses the same copied-state Y turn forecast as the risk indicator,
and cannot commit movement or modify the encounter.

## Verification and dependency

A portable renderer regression selects a reachable cursor tile,
checks that the exact projected marker pixel appears, confirms
the entire battle remains unchanged, verifies hidden and restored
risk display, and ensures moving the cursor to a blocked tile and
cancelling selection remove the marker. Existing enemy forecast,
hero HP/guard, replay meter and NeXium tests remain active.

Stage234 is stacked on Stage233 PR #117. Stage233 must pass full
independent real-NeXium and host CI and merge into `main` first.
Then Stage234 must target `main` and pass a fresh independent
full CI matrix before merging.

No original PS3 assets, proprietary map data, or physical Nintendo
Switch gameplay are used or verified.
