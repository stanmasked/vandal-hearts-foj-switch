# Stage 227 — full synthetic tactical victory in a real NeXium guest

This milestone checks the **whole generated-only 8×6 homebrew battle**
through the actual Nintendo Switch NRO running in NeXium, rather than
passing isolated native C simulations alone.

## Single-guest playthrough

After building and validating `foj-isometric-research.nro` with devkitA64,
the workflow uses a headless software-Vulkan NeXium session to inject
controller events using keyboard defaults confirmed in the emulator's
`controller_config.rs`:

- Starting hero (1,2), enemy (6,3): save an initial screenshot
- **A, Right×4, A:** move the hero to (5,2)
- **Y:** enemy advances adjacent and hits hero; capture `battle-turn1.png`
- **Right, X:** strike enemy once; capture `battle-hit1.png`
- **Y:** receive a second enemy attack; capture `battle-turn2.png`
- **X:** kill synthetic enemy; capture `battle-victory.png`
- **Y:** attempt invalid post-victory action; capture
  `battle-terminal-y.png`

All six PNGs are imported from the running guest application window.
Nothing is replaced by a host reference image. The verifier checks the
invented CPU framebuffer's specific red enemy, blue hero, background
and green victory-indicator palettes. It requires observable enemy HP
loss after first X, hero HP loss after second Y, removal of the enemy
sprite, a victory banner and unchanged combat evidence after terminal Y.

Nine independent generated-only fixture scenarios cover success and
false-positive rejection for absent attacks, absent damage, fake or
missing victory, enemy still visible, changes after terminal Y, blank
or mismatched guest frames. Artifacts include guest screenshots,
sanitized startup log, nightly NeXium archive SHA-256 and a structured
success receipt. The verifier never asserts original source-game
mechanics and never reads user-owned PS3 resources.

## Dependencies

Stage227 builds on Stage226 PR #110, which proves actual guest B-move
undo. Keep this change in Draft and stacked until Stage226 passes
independent CI and merges with `main`. Then retarget Stage227 to
`main`, trigger a fresh complete host/NRO/NeXium test and merge only
if each check passes. Neither a successful emulator pass nor the
fictional synthetic battle establishes physical Switch compatibility,
authentic Vandal Hearts: Flames of Judgment gameplay, or a finished port.
