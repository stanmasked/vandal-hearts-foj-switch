# Stage238 — real NeXium evidence for cache reuse

Stage237 PR #121 merged the cursor-invariant movement threat preview cache
to `main` with 30/30 successful GitHub status checks. Host tests confirmed
the cached and uncached threat maps and rendered pixels are identical; they
did **not** prove the installed Switch NRO actually used the cache.

This step instruments only the generated 8×6 research guest. After each
CPU-rendered frame, it draws two small diagnostic tiles:

- **Generation**: muted gray if no current matrix, cyan for exactly one
  matrix computation, gold for exactly two, magenta if more than two.
- **Reuse**: muted gray before a real hit, mint when cache hits > 0.

The indicators use `FojBattleThreatCache`'s existing counters, and are drawn
**after** combat state simulation and rasterization. They cannot affect
movement, damage, forecasting, replay or terrain. Cache tiles occupy
x=400..407 and x=412..419, y=12..19 in the 1280×720 framebuffer. The
Stage229 replay meter occupies x=256..383 at the same height; C11
`_Static_assert` checks the separation during every native build.
The muted-gray invalid marker and the violet no-hit marker have deliberately
nonoverlapping RGB tolerances, after an initial synthetic control exposed
their former color alias.

The new `stage238-nexium-threat-cache.yml` builds the real
`foj-isometric-research.nro` with devkitA64, boots it in software-Vulkan
NeXium and captures nine actual guest screenshots:

1. Initial, before selection: invalid matrix, no hits.
2. A hero selected: first calculated matrix, at least one cache hit.
3. D-pad hover: still first generation and hits present.
4. Right-stick overlay hidden: no new generation.
5. Overlay restored: no new generation.
6. B selection cancelled: no active matrix.
7. ZR guarded and hero reselected: exactly second generation.
8. D-pad hovered again: remains second generation, hits present.
9. Y ends turn: no active movement prediction.

Actual NeXium screenshot evidence from run `39179738519` confirms that
the raw x=400/x=412 framebuffer markers land at x=409..415/x=420..427,
y=12..18 in the 1280×720 GUI screenshot. The original Stage238 screenshot
validator incorrectly classified its **whole-image** color histogram:
22 unrelated gray GUI pixels were mistaken for an active invalid-cache
marker during the selected frame. The updated validator samples only
nonoverlapping marker neighborhoods (x=407..417 and x=419..429,
y=10..20), retaining the original fail-closed bounds on marker counts.
Two further synthetic tests assert that unrelated GUI colors do not cause
false rejection and that misplaced markers cannot impersonate valid evidence.
The nine previously captured real guest frames satisfy these region-local
checks; fresh latest-head CI is still required before merging.

The verifier requires the existing Stage231 battlefield/hero/enemy palette
as a prerequisite and then checks both unique counter colors in each frame.
Thirteen generated screenshot controls include missing hits, stale generations,
extra recomputations, blank frames and wrong sizes. Guest screenshots and an
asset-free JSON receipt are uploaded as CI artifacts.

The evidence demonstrates a **reduction in redundant forecast recomputation**,
not a quantified FPS gain or correctness of the original PS3 game rules.
No copyrighted PS3 resources, licensed game content or encryption keys are
included or distributed; physical Switch testing remains outstanding.
