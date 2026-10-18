# Stage 224 — genuine NeXium guest comparison of synthetic guard damage

Stage224 strengthens the Stage223 guest battle evidence with a defensive
choice: whether the actual Nintendo Switch research NRO responds to
**ZR** by reducing the next enemy strike.

## Two independent guest sessions

The workflow compiles and validates the existing isometric battle NRO and
launches it in the same headless NeXium environment as Stages182/223.

Starting from identical generated-only battlefield states, it uses
previously verified emulator keyboard defaults:

1. Press A (keyboard `c`), cursor Right four times, press A again to
   move the invented hero from (1,2) to (5,2).
2. **Normal run:** press Y (keyboard `z`), capture enemy-turn result.
3. **Guarded run:** start a fresh NRO, repeat the same hero movement,
   press ZR (keyboard `t`), capture active defensive marker, then
   press Y and capture enemy-turn result.

Both scenarios begin with the enemy at (6,3); it moves to (6,2) and hits
the nearby hero. The invented engine deals **2 HP without guard** and
**1 HP with guard**, so the renderer's 40-pixel-wide, 5-row blue HP
bar should show about 25 extra blue pixels after the guarded turn.
A bright mint 7×7 marker must appear while guarding and vanish after Y.

The fail-closed verifier checks the invented background and both sprites
in all three *actual emulator captures*, requires the initial guard
marker, requires its expiration in the two after-turn images, verifies
the hero bar difference is bounded and positive, and ensures enemy and
hero positions match between otherwise identical scenarios. Seven
generated-only fixture tests reject equal damage, fake marker,
stale marker, missing enemy, changed positions and blank screens.

The only inputs are generated synthetic homebrew assets; no private
PS3 COLL/mesh/animation/media data is uploaded. A successful run would
prove only ZR-driven guard behavior of the invented homebrew prototype
**in NeXium**, not source-game defense statistics or physical Switch
execution.

## Integration gate

Stage223 PR #107 passed independent checks and merged into `main` at
`c1f6cc9bdce6600bf4242b65a8bd2bbdc2b9af7e`. Stage224 now targets
`main` and must pass its own Python 3.11/3.13 and actual NeXium guest
screenshots again on this new base before merging.
