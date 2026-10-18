# Stage235 — actual NeXium predicted enemy landing cell proof

Stage234 provides a purple marker for the enemy cell predicted by the
**same** invented next-Y simulation used for movement risk. Stage235
checks that this projected marker reaches the actual framebuffer of
the synthetic Nintendo Switch research homebrew.

## Six real guest captures

A devkitA64-built `foj-isometric-research.nro` is launched under
NeXium with software Vulkan; the existing NeXium default keyboard
bindings are used to capture:

1. Initial map, hero not selected — no purple marker
2. Press A — current cursor is on hero; no target destination or marker
3. Press Right to hover legal generated tile (2,2) — purple marker
   appears near the enemy's predicted position (6,2)
4. Press right-stick click — purple marker disappears
5. Press right-stick again — identical purple marker returns
6. Press Up to hover blocked (2,1) — no purple marker

The verifier rejects blank/wrong-size frames, premature/missing/stale
marks, marks outside the bounded region for generated tile (6,2), and
failure to restore the same marker after the visibility toggle. Ten
generated-only Python test cases cover expected and adversarial data.
The expected location and region are specific to the invented 8×6
test map; they are **not** imported original PS3 enemy pathing.

Evidence consists of synthetic PNGs and the pinned NeXium archive
checksum; original game assets remain entirely private.

## Integration

Stage234 PR #118 passed all 15 independent GitHub Actions checks and
merged into `main` at `53c60b0a2dae185348d437d31e0e246546b0a4cd`.
Stage235 now targets `main`; independent fresh host, NRO and real
NeXium checks must pass on the latest head before integration.

No physical Nintendo Switch or original PS3 mechanics are verified.
