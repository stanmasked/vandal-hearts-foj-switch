# Stage247 — exact-scene base-raster reuse (Nintendo Switch research)

## Finding from Stage246

The **generated** 8 × 6 CPU isometric base terrain accounted for the large
majority of the 32-frame four-phase measurements in genuine NeXium evidence.
This is *not* the original PlayStation 3 FoJ renderer or a hardware Switch
benchmark. The next isolated experiment asks whether retaining an
**unchanged full base image** saves this work during idle display frames.

## Correctness model

- Base raster includes the background, all 48 generated cell faces, height
  occlusion, highlighted path/reachability, generated hero/enemy tokens and
  selected cursor. It is **not** a texture/model cache and contains **no PS3
  assets**.
- Cache admission compares **all** fields in `FojDemo`: 48 elevations and
  blocked flags, hero/enemy positions, cursor and selection state.
  Field-by-field comparison intentionally ignores irrelevant C padding.
- A scene-exact hit uses row-wise copy of the known base pixels; a miss
  invokes the unchanged original `foj_iso_render` painter and refreshes
  the cache. Destination row padding is untouched. Unsupported dimensions
  bypass the cache and draw normally.
- Battle forecasts, threat-risk painting, HP/guard/attack overlays, victory
  bands, external COLL visualization and replay control **still run for every
  frame**. Their state is never cached. No battle action is replaced or
  skipped.
- Cache pixel storage is bounded to 1280 × 720 RGBA32 (3,686,400 bytes,
  about 3.52 MiB). It is a caller-owned object allocated in global/static
  storage in the guest, not on a small thread stack. Default NRO has no
  cache allocation or new timing probes.
- `foj_iso_render_battle_profiled` and production
  `foj_iso_render_battle_cached_options` retain their existing interfaces;
  only the explicit research entry point
  `foj_iso_render_battle_profiled_base_cached` enables reuse.

## Evidence contracts

1. Strict C11 GCC, Clang and UBSan tests compare full output pixel-by-pixel
   with the uncached full battle renderer after warm/cold frames,
   cursor/selection/terrain changes, HUD-only changes and enemy defeat.
   They also check all scene key fields, padded stride, unsupported
   dimensions and invalid input handling.
2. `make -f switch/Makefile build/foj-isometric-base-cache-profile.nro`
   builds a **research-only** `FOJ_STAGE247_BASE_CACHE=1` guest. It includes
   the Stage246 exclusive four-phase timer. The normal NRO is unchanged.
3. At top-right x=1252,y=12 the guest prints an independent 8×8 green
   tile for a genuine same-scene base reuse, or red for a cold/invalidation
   miss. This is not an animation or fake HUD decoration: the color is
   directly determined from `foj_iso_base_cache_draw`'s hit result.
4. The Stage245 input driver captures nine actual NeXium guest states
   with 32+ rendered frames between actions; the Stage247 checker
   independently verifies all nine green hit tiles **and re-runs**
   Stage238 threat-cache gameplay proof, Stage241 render receipts, and
   Stage246 all-four-phase barcode validations. SHA-256 of each actual PNG
   is retained in the report.

This validates *pixel-equivalence and that warm cache reuse actually
occurred*. It is not proof of improved hardware FPS or end-to-end game
responsiveness; no physical Switch data or original PS3 models are used.
Cross-run comparison to Stage246 is descriptive only, not a controlled
causal benchmark (different NeXium runs may drift). Full within-process
A/B comparisons should be a separate experiment if needed.

## Exit gate

Only accept PR after native compiler/sanitizer tests, devkitA64 NRO
validation, genuine nine-state NeXium evidence and all triggered
regression workflows pass. Keep Draft until then.
