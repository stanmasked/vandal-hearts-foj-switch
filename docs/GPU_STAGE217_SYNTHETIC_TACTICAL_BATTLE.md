# Stage 217 — playable synthetic tactical-turn research loop

This is a generated-only, deterministic prototype — **not** the PS3 battle
system, animation rules, narrative, enemy AI or original-game balancing.

## What is now interactive

Two existing Nintendo Switch research NROs now share
`core/tactical_battle.c`:

- `foj-switch-research.nro`: console-grid version with turn, HP and action
  messages.
- `foj-isometric-research.nro`: rendered board, movable character/enemy
  tokens, health bars, removal of the defeated enemy token and a
  victory/defeat color strip.

Controller bindings: D-pad moves the grid cursor; A selects the hero and
confirms movement; B cancels selection; X attacks the enemy under the
cursor if it is orthogonally adjacent and the elevation difference is
legal; Y ends the turn; MINUS resets this synthetic battle; PLUS exits.

Each turn allows at most one move within the original demo's four-cell
movement budget and one adjacent attack (order can vary). A selected
unit cannot attack until selection is canceled or movement confirmed.
A legal attack deals 3 invented HP of damage. After Y, the synthetic
enemy takes one shortest-path step along allowed ramps toward the hero
and attacks for 2 HP if adjacent. Equal-cost paths use fixed
north/east/south/west tie-breaking. All pathfinding uses a fixed 8x6
board, fixed-size BFS arrays, and no random choices or allocations.

The invented combat begins with 8 hero HP and 6 enemy HP; removing all
enemy HP wins, and removing all hero HP loses. Both terminal outcomes
reject further battle actions until restarted. A blocked or disconnected
enemy ends its turn without acting. There are no animations or source
assets attached to these state changes yet.

## Validation

`tests/test_tactical_battle.c` covers eight generated-only scenarios:
selection and once-per-turn movement, attack cooldown and victory,
invalid targets/heights, repeatable enemy behavior, defeat/reset,
inaccessible terrain with saturated turn counter, null-safety,
and a complete initial-position-to-victory controller-style playthrough.

`tests/test_isometric_demo.c` also compares the original generated map
with HP overlays and validates distinct victory/defeat result strips.

`.github/workflows/ci.yml` compiles both portable host programs with
strict C11 warnings; the battle core additionally runs under UBSan.
The existing `switch-nro.yml` workflow builds the actual research
NROs using devkitA64/libnx, subject to available CI infrastructure.

## Scope and next integration

No original PS3 resources, executable, captures, map numbers, or media
are included in source control or CI. The synthetic terrain elevations,
enemy HP and pathfinding are not assertions about the original game.
The next gameplay-oriented milestone is to connect the tactical state
machine to locally inspected real collision cells and playable scenario
data, retaining private asset boundaries and independent correctness
checks before any claim about authentic FoJ combat.
