# Stage 219 — deterministic enemy-turn forecast before committing Y

Stage219 advances the **invented** 8×6 Switch tactical prototype. It does
not reconstruct enemy AI, battle damage, turn order or any other rule from
the PS3 original.

## Player-facing changes

Before pressing Y to end the hero's turn:

- The console research NRO prints a live preview of the enemy's next
  position, the hero's predicted HP and the action that will occur.
- The isometric research NRO draws an amber ring on the enemy's predicted
  next position when it will advance. A thin amber bar along the top
  warns that ending the turn now will inflict enemy damage.
- After battle ends the forecast becomes unavailable; the existing
  victory/defeat indicator remains authoritative.

Preview updates from the current state, so it reflects any legal hero
movement or attack before Y is pressed. It cannot move the enemy,
consume the hero's action budget or change the game turn.

## Engine behavior

`foj_battle_forecast_enemy_turn` takes the current fixed-size battle
state by const pointer, creates one stack-local copy, and invokes the
**same** `foj_battle_end_turn` implementation used for real actions.
It returns the resulting event, enemy destination, hero HP, turn number
and terminal state. Rejected/terminal inputs produce no forecast; the
output is zeroed on such rejection.

This avoids a separate, potentially divergent AI-prediction algorithm.
It does not use randomness, dynamic allocation, external content or any
user-provided PS3 data. It is independent of Stage218's optional raw COLL
diagnostic channels, which continue to have no effect on movement or
attacks.

## Tests and privacy

Four additional generated-only tests confirm:

1. Forecasts match several actual committed turns without mutating the
   input state.
2. Lethal enemy attacks are forecast accurately, and terminal or null
   requests reject safely.
3. Disconnected enemies and saturated turn counters remain deterministic.
4. The preview recalculates after a four-tile hero move and matches the
   actual next enemy attack without consuming any player actions.

An additional isometric test checks the destination ring, imminent-attack
warning, and victory-indicator precedence. The existing Stage217 strict
C11/UBSan and rendering CI runs cover all updated portable C sources.

No PS3 models, maps, animation clips or screenshots are committed. This
feature is a gameplay-prototype usability step rather than a fidelity
claim about Vandal Hearts: Flames of Judgment.

Dependency satisfied: Stage218 PR #102 passed all eight workflows and
merged into `main` at `96abfff15c4f70d8f793ccc786691285e0a8346c`.
Stage219 targets `main`. Keep Stage219 Draft until independent Python
3.11/3.13, host C/UBSan and Switch NRO workflows all pass.
