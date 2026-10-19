# Stage249 — scene invalidation refill and within-guest stability (synthetic FoJ research)

## Why

Stage248 demonstrated warm-cache vs uncached raster differences in one genuine
NeXium guest, but a single 32-pair mean per snapshot does not show
between-window jitter or the cost of a changed scene. Stage249 adds two
independent checks without changing default rendering code.

## Measurement

- Each scene begins with a **measured cold** call to
  `foj_iso_base_cache_draw` on a newly invalidated private cache, then a
  **measured warm** row-wise copy of the identical base map. Screens are
  pixel-identical by `memcmp`. The reported cold/warm cost is base-raster
  work *only*, excluding battle HP/threat overlays.
- Afterwards the existing Stage248 complete-battle private paired A/B
  renderer runs **32 pairs per window**, AB/BA order. Store the minima and
  maxima of each arm's full frame mean across completed windows; the third
  barcode is the **larger** of their two min–max spreads.
- The stability status can be green **only after at least three independently
  completed 32-pair windows** and a valid cold/warm parity receipt (plus
  Stage248 per-pair exact pixel identity). Scene changes, cursor changes,
  terrain mutations, guard/HP updates or threat visibility reset these
  completed-window measurements. No stability threshold is imposed to
  mask real timing jitter.
- Stage249 guest-only optical receipt at y=12:
  - x=536: 16-bit microseconds for *cold base recompute*;
  - x=608: 16-bit microseconds for *warm base copy*;
  - x=680: 16-bit microseconds for *largest observed 32-pair mean spread*;
  - x=752: 8×8 status (amber insufficient windows, red parity/clock failure,
    green at least three complete valid windows).
- Inherited Stage248 full-raster pair bars at x=780/852 and parity x=924,
  Stage246 four exclusive phase bars starting x=948 and Stage247 base reuse
  at x=1252 remain independently checked. The visible generated battle is
  untouched by the private measurement buffers.
- Preserve nine genuine 1280×720 NeXium screenshot SHA-256 digests; the
  optical decoder re-runs all inherited Stage238, 241, 246, 247 and 248
  checks before accepting Stage249 receipts. The same captured screenshot
  can contain four distinct validated guest telemetry families, but it is
  still **one observation**, not four independent benchmarks.
- Cold refill itself is **a different operation** from invalidating the
  cache pointer or from end-to-end scene transitions. It must not be
  described as entire game-state transition cost.

## Memory and build isolation

Stage249 is compiled only by the explicit
`build/foj-isometric-base-cache-stability.nro` target with the
`FOJ_STAGE249_STABILITY=1` gate. Its private Stage249 base cache replaces,
rather than adds to, Stage248's private cache. Two scratch 1280×720 RGBA32
buffers consume 7,372,800 bytes; visible Stage247 base cache and private
Stage249 base cache each include a 3,686,400-byte pixel raster plus small
metadata. The aggregate of these named allocations is statically required
to remain below 17 MiB. The platform framebuffer and ordinary engine data
are *not* included in that bound.

This proof tests generated 8×6 CPU software rasterization, **not**
original PS3 terrain art or engine, physical Switch GPU, FPS or presentation
latency. Never claim an all-game speedup or an original-game port.

## Exit gate

Require native GCC, Clang and UBSan controls; dedicated devkitA64 NRO;
nine genuine NeXium states with cold and warm receipts and at least 3×32
valid paired windows per scene; inherited independent validations and a
clean regression matrix. Preserve the original PS3 resources unchanged.
