# Stage 236 — full parity between predicted danger and real controller replay

The synthetic eight-by-six Nintendo Switch research encounter now has
several independent movement aids: legal path, predicted next enemy cell,
and the HP loss if the player ends the turn. The next correctness gate
checks that these are not merely self-consistent **with another forecast**:
they must match the result reached by actual game button events.

## Exhaustive source-only integration test

For each reachable move destination on the invented 8×6 battlefield,
the new `tests/test_battle_threat_replay_parity.c`:

1. Obtains the complete `foj_battle_preview_movement_threat` risk map
   from an A-selected hero, preserving the original battle byte for byte.
2. Starts a fresh battle and drives real `foj_replay_record` commands:
   optionally **ZR**, then **A**, individual D-pad cursor movements,
   **A** to commit the destination, and **Y** for enemy action.
3. Demands the existing noncommitting Y forecast agree with the live
   event, HP, enemy coordinate, turn counter and battle outcome.
4. Demands the original movement risk matrix give **exactly** the real
   HP loss and next enemy coordinate for each destination.
5. Calls the deterministic history validator after every controller
   event and checks both safe and dangerous destinations.

An additional low-health run gives the hero only one synthetic HP,
checks a defeated/terminal result at close range with and without
guard, and verifies that predicted damage, destination and resulting
outcome still agree with the actual Y action. Finally, occupied,
blocked and current-hero cells cannot become legal routes even if
the player moves the cursor and tries A.

The five test groups are executed with strict C11 `-Werror` and
UBSan on both Python 3.11 and 3.13 research-tool jobs. Existing
NeXium, generated rasterizer and devkitA64 builds remain required.

## Privacy and integration

All tested routes, damage values and screenshots use generated-only
maps and independently implemented mechanics. This is **not**
verification of original PS3 tactical rules or of physical Switch
gameplay; the user-owned package and extracted resources stay private.

Stage235 PR #119 passed independent research, guest NeXium and COLL
checks and merged into `main` as
`977423e61e52ce2822c178d756c1af39d0fd1a10`. Stage236 now
targets `main` and must pass fresh exhaustive C11/UBSan, host tests,
Switch NRO and NeXium CI on its latest head before integration.
