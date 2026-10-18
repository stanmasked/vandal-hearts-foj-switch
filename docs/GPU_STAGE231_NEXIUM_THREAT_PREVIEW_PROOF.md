# Stage 231 — independently verify movement threat preview in actual NeXium

Stage230 adds read-only safe/risky move hints for the **invented 8×6
tactical battlefield**. Stage231 tests whether these hints actually
appear, update and disappear in the running Nintendo Switch research NRO.

## Guest sequences

An asset-free homebrew NRO is built with devkitA64 and launched twice
under NeXium, Xvfb and software Vulkan. The workflow records the
NeXium nightly archive digest and captures five **real guest frames**.

The default Switch-to-keyboard mappings are A=`c`, B=`x`, ZR=`t`,
DRight=`Right`. With the original generated hero (1,2), enemy
(6,3), heights and ramps:

- Initial: neither safe nor dangerous destination indicator appears
- A: movement selection shows safe tile (2,2) in teal and incoming
  2-HP danger for (5,2) as two orange ticks
- Right: changing cursor leaves destination-risk overlay stable
- B: cancelling selection removes all threat markers
- Fresh guest, ZR then A: guarded threat preview keeps tile (2,2)
  safe and reduces tile (5,2) from two orange ticks to one

The verifier requires the actual 1280×720 NeXium screenshot and
synthetic hero/enemy/background. Since NeXium scales the guest inside a
letterboxed window, it counts the teal and orange marker pixels within
two small, bounded screen regions around the relevant tiles, rather
than sampling unscaled framebuffer coordinates. These bounds and the
observed 15/32/16 pixel signatures were calibrated against genuine
failed-run PNG artifacts, not guessed or weakened globally. It still
rejects static screens, missing units, early, absent or stale overlays,
and any failure to reduce two predicted orange HP ticks to one with ZR.
Eight generated-only positive and negative PNG tests regress these
requirements without relying on the emulator.

## Scope, safety, dependencies

Stage231 contains no original PS3 code, assets, maps or combat rules.
The predicted movement and damage are purely from the existing
synthetic test encounter; no physical Nintendo Switch test is implied.

Stage229 PR #113 and Stage230 PR #114 passed their respective latest-head
CI matrices and merged with `main`. Stage230 was merged as
`719af4fb3e6b4d28b414fd843c49394e12ec5115`. Stage231 now targets
`main` and must independently pass the complete new guest NeXium,
strict C/Python, NRO and generated renderer tests before merging.
