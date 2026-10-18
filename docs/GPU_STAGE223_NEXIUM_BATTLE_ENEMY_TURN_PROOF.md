# Stage 223 — real NeXium guest verification of synthetic enemy turns

This stage verifies **behavior of the actual interactive isometric
Nintendo Switch research NRO inside NeXium**, instead of treating SDK
compilation or portable host rendering as proof of emulated gameplay.

## Guest procedure

The workflow `.github/workflows/stage223-nexium-battle.yml` builds the
existing `foj-isometric-research.nro` using devkitA64 and validates the
binary. A separate Linux job downloads the same NeXium nightly channel
used by the earlier Stage182/193 tests, records the archive digest and
launches the built research NRO under Xvfb and software Vulkan.

After collecting the initial actual guest screenshot, it sends two
separate, explicit Switch **Y** button transitions through NeXium's
previously verified default keyboard mapping (`z`). It captures the
guest screen after each button event, not a host-generated replacement.

`tools/foj_stage223_battle_guest_check.py` requires all three images to
contain the synthetic background, blue hero and red enemy colors. It
measures the enemy sprite's red-pixel centroid and requires a plausible
change on **each** input. Static frames, blank screens, disappearing
heroes, mismatched dimensions and implausible jumps fail closed.

The project’s invented map begins with the enemy at (6,3). The deterministic
BFS is expected to advance it to (6,2), then (5,2), while the hero remains
at (1,2); the verifier checks visible movement independently instead
of assuming compilation implies input dispatch.

Six positive/negative unit tests use **generated** PNG fixtures to
regress the classifier without running a guest. Screenshots, receipt,
and sanitized startup evidence are uploaded only as CI artifacts
generated from the invented battle (no proprietary PS3 assets).

## Interpretation

A green Stage223 confirms two enemy transitions in the *actual emulated
synthetic research NRO*. It does not establish correct original PS3
enemy AI, authentic animations or mission assets, physical Nintendo
Switch behavior, or a playable port of the commercial title.

Dependencies satisfied: Stage221 PR #105 and Stage222 PR #106 have
merged into `main` (Stage222 merge `3215c978`). Stage223 now targets
`main` and requires an independent NeXium run and Python 3.11/3.13
verification against that main branch before merging.
