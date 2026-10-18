# Stage 222 — read-only hero attack forecast in synthetic tactical battle

Stage222 adds another **invented-gameplay choice preview** to the 8×6
research NROs. It does not infer PS3 attack ranges, damage statistics,
animation timing or authentic Vandal Hearts: Flames of Judgment rules.

## Controls and visual behavior

Before pressing **X** to attack, move the cursor onto the synthetic enemy.
If the normal attack can legally execute (hero adjacent, elevation step
allowed, selection canceled and attack unused this turn), the console
NRO shows the enemy's predicted remaining HP and whether the hit wins.

The isometric research NRO displays a golden outline around a legal
target and a gold bar under the normal red enemy HP bar indicating the
**post-hit** HP. No prediction is shown if the hero has guarded with
**ZR**, has already attacked, the cursor targets another square, the
target is out of range or the battle has ended.

## Rule consistency

`foj_battle_forecast_attack` does not have a second target validator:
it makes a temporary copy of `FojBattle` and invokes the same
`foj_battle_attack` routine as the X button. It reports the real
action event, post-attack HP and win/ongoing outcome, or declines with
a zeroed output. It cannot consume a move, attack or guard action, nor
change any unit position or HP.

The existing Stage219 next-enemy-turn forecast and Stage220 guard
status continue to use the same shared battle model. Stage218–221
optional COLL observations remain separate diagnostics and are never
treated as movement, terrain or attack rules.

## Generated-only tests

Three additional portable C battle checks cover unchanged input state
and parity with real hits, lethal victories and invalid targets, and
guard/selection/elevation restrictions. The isometric rasterizer
checks the golden preview marker, verifies no state mutation and
ensures the marker vanishes when guarding makes attacking illegal.

The existing strict-C11, UBSan, research Switch NRO and generated
isometric visual workflows cover all modified files. No proprietary
game files, original maps, models, textures or audiovisual assets are
included in this branch or its CI.

## Integration gate

Predecessor stages are integrated: Stage220 PR #104 and Stage221
PR #105 have merged with `main` (Stage221 merge `d00e454b`).
Stage222 now targets `main` and must pass independent Python 3.11/3.13,
C/UBSan, NRO, NeXium and generated-image CI on its new head before merging. This is an
experimental homebrew battle prototype, not a finished game port.
