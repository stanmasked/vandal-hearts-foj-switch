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

Stage226 PR #110 passed all independent checks and merged with `main`
at `c83ff2482e4625f4f80e872c5b10228894596987`. Stage227 now
targets `main` and must pass fresh independent Python 3.11/3.13,
NRO and actual NeXium screenshot checks on its new head before merging. Neither a successful emulator pass nor the
fictional synthetic battle establishes physical Switch compatibility,
authentic Vandal Hearts: Flames of Judgment gameplay, or a finished port.
