# Stage229 — actual guest proof of deterministic input count

Stage228 records a bounded sequence of player commands in the invented
8×6 tactical battle and verifies that reconstructing the same input
history produces the identical state. Stage229 adds independent
**guest-observable evidence that the history actually advances**.

## Visible input history

The isometric research NRO has a small pixel-only bar from x=256–383,
y=12–19, displaying all 128 possible command positions. One colored
vertical pixel-column represents one recorded input; the remainder are
a dark neutral shade. The original green/red/amber replay verification
square remains independent at x=240–247. Both elements sit outside
NeXium's built-in performance overlay near the top-left screen corner.

A standalone `core/battle_replay_meter.[ch]` module validates canvas
width, height, stride and command-count bounds before drawing. It
modifies no original PS3 data and never changes the combat state.

## Actual guest exercise

Stage229 reuses the proven Stage226 NeXium button script and its four
actual guest screenshots:

- 0 inputs: initial scene
- 4 inputs: A, Right, Right, A — hero has moved
- 5 inputs: B — last movement undone
- 8 inputs: A, Right, A — different movement selected

The verifier runs the existing Stage226 movement-state check **first**,
then counts a unique replay-bar pixel color in each real guest capture
and demands progression proportional to 0,4,5,8 (with bounded screen
scale). It rejects a static, missing, inflated or forged progress bar.
Six generated-only Python cases check valid history and failure modes.

Portable C11 and UBSan checks test the meter's exact values for 0,
4, 5, 8 and the maximum 128, padding sentinels, undersized buffers
and invalid counts. A separate GitHub Actions workflow runs those
host tests, compiles the research NRO with devkitA64, starts the actual
homebrew in NeXium and preserves generated-only evidence.

No original PS3 asset or gameplay rule is involved. The meter only
validates the synthetic homebrew implementation on an emulator,
not physical Switch operation or completed porting.

## Integration gate

Stage228 PR #112 passed all twelve independent checks and merged into
`main` at `e8c8998a47a0926203f59eb74f79ff9cb02e8537`.
Stage229 now targets `main`; the meter and NeXium evidence require
fresh independent strict C11/UBSan, NRO and emulator verification.
The first guest run revealed that NeXium's own performance overlay
obscured the initial upper-left meter. The meter was relocated beyond
that overlay without weakening pixel-count requirements.
