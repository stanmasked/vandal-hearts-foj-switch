# Stage 220 — guarded stance in the synthetic Switch tactical battle

This is a **playability feature for invented 8×6 combat**. It does not
reproduce or authenticate a defensive ability from the original PS3 game.

## Player interaction

Press **ZR** to defend. Guarding consumes the hero's one available
attack for the turn but does **not** prevent an unused movement action.
Guard is rejected while a unit is selected, after attacking, after
already guarding, or after a battle finishes. Press **Y** to end the turn.

If the enemy reaches the hero and attacks on that turn, guarding
reduces the invented enemy damage from 2 HP to 1 HP. Guard expires
immediately after the enemy action, including when the enemy cannot
reach the hero. It does not persist across turns or cancel lethal
damage at 1 HP. The battle's existing normal attack, movement and
terminal rules remain unchanged.

The Stage219 enemy forecast uses exactly the same
`foj_battle_end_turn` on an isolated state copy, so its expected HP,
enemy destination, next turn number and possible defeat automatically
reflect guarding. The live console UI displays `Guard=active`, and
the isometric NRO displays a mint marker beside the hero until the
guard is consumed. No camera, original assets or COLL flags influence
the protection.

## Validation

Four new synthetic C battle tests check:

- Guard mitigates an adjacent enemy hit and resets before the next one
- Guard/attack exclusivity while allowing a still-unused move
- Guard expiration when a blocked enemy cannot attack
- Lethal 1-HP boundary, forecast parity, reset and terminal rejection

An additional renderer test checks marker appearance and removal
after a turn. The inherited CI compiles both research NROs, builds
strict C11 host test binaries and runs the battle and renderer checks.
No PS3 game bytes, original map rows, screenshots, scripts or proprietary
gameplay values are included in GitHub or its workflow artifacts.

## Integration gate

Stage220 follows Stage219 PR #103. Stage219 must pass Python 3.11/3.13,
host C, isometric rendering and NRO builds before merging. After that,
retarget Stage220 to `main`, require fresh independent CI and only then
merge. This is still a synthetic homebrew battle prototype, not a
playable Vandal Hearts: Flames of Judgment port.
