# Stage 228 — deterministic, bounded controller history for synthetic combat

This adds a small replayable **debugging instrument** to the invented
8×6 Nintendo Switch combat research NRO. It is **not** a PS3 battle
serializer, authentic original-game command log, or saved game format.

## What is recorded

The two interactive battle NROs now route each actual battle input
through a shared, portable `core/battle_replay.[ch]` dispatcher:

- Four individual D-pad cursor moves
- A: select hero / commit movement
- B: cancel selection / undo an uncommitted move
- X: attack, ZR: guard, Y: end turn
- Minus: reset the synthetic battlefield

The log holds **at most 128 commands**, with one byte per command and
no heap allocations. Rejected actions are intentionally recorded as
input, because pressing X out of range or Y after a victory is part of
the real controller history. The COLL visualization controls L/R/ZL
never enter the log, because they do not touch battle state. Plus
still exits the NRO.

`foj_replay_reconstruct` starts a fresh generated battle, applies
the recorded inputs using the **same action functions** as gameplay,
and only writes the reconstructed result if every byte is valid.
`foj_replay_matches` checks that the replay produces the identical
deterministic `FojBattle` state without modifying the live game.
Unknown commands, bad pointers, truncated state and log overflow are
fail-closed. At exactly 128 commands new battle input is refused
instead of silently dropping records or letting its unlogged effects
change the active game.

The console NRO prints `Input replay: N/128, VERIFIED/MISMATCH`. The
isometric NRO overlays a small 8×8 audit square in the top-left:
green = deterministic match, red = mismatch, amber = full log. It
rechecks only after actual battle button events, not continuously.

## Testing and privacy

Six generated-only portable C scenarios verify a complete two-hit win,
B-move undo and alternate route, ZR defense and invalid attacks,
restart in the middle of a session, rejecting corrupt logs without
altering the destination, and preserving both input history and
battle state at maximum capacity. Strict C11 and UBSan checks run
in both Python 3.11 and 3.13 workflows.

No original PS3 executable, textures, maps, screenshots, keys, or
user-owned assets are embedded in GitHub or CI artifacts. This is
still a synthetic homebrew battle, not a completed remake.

## Integration gate

Stage227 PR #111 passed CI and merged into main (dbc71eae). Stage228 follows it, and, which supplies independent
guest-emulator full victory evidence. Merge Stage227 only after all
latest-head CI succeeds; then retarget this PR to `main` and require
fresh strict C11/UBSan, Switch NRO, guest NeXium and visual CI before
merging Stage228.
