# Stage252 — compact cache endurance and deterministic failure recovery

This stage exercises only the **generated 8×6 CPU base raster**, not
the original PS3 game code, models, art, GPU pipeline or real Switch FPS.

## Workload and accounting

The opt-in `FOJ_STAGE252_STRESS=1` NRO performs **96 cold→warm
rendering cycles** before entering the ordinary nine-state synthetic
battle. It alternates 320×180, 640×360 and 1280×720, changes synthetic
terrain and cursor data, and uses two independent reference buffers.
Every warm image is compared byte-for-byte with the cold image and an
independent uncached `foj_iso_render` output. The default NRO and the
Stage251 NRO do not enable the fault-injection field or stress runner.

Eight deterministic allocation failures are injected at cycle indices
0, 13, 26, 39, 52, 65, 78 and 91, **only at a real reallocation site**.
When a simulated malloc fails, the old buffer has already been
released, the cache must be invalid and empty, and the following
allocation must recover. A missed draw must never be reported as a
successful cached hit. Stress exits after releasing its last raster.

Expected local counters: 96 completed cold/warm cycles, 8 injected
allocation failures and recoveries, 96 successful allocations,
96 releases and a maximum single requested pixel payload of
3,600 KiB. Each cycle compares active pixels; row stride and budget
rejection have additional native tests. The counters do **not** measure
allocator overhead, physical memory RSS, fragmentation, system-wide
RAM or actual game frame performance. This does not constitute a
general proof that malloc can never fail under arbitrary conditions.

## Reproducible validation

- `tests/test_stage252_compact_stress.c`: runs two successive full
  96-cycle stresses (the second without restarting the process),
  checks recovery from an injected failure, validates release
  accounting, valid/invalid optical draw bounds and explicit budget
  rejection.
- Native: GCC, Clang, UBSan and Clang ASan/LSan. Previous Stage251
  exact-size and Stage248–250 fixed-cache tests must remain green.
- Switch: separate `build/foj-isometric-compact-base-cache-stress.nro`
  constructed by devkitA64, never the default target.
- NeXium: one actual emulator guest with nine normal synthetic battle
  screenshot states, *all Stage251 ancestor receipts* and independent
  Stage252 optical y60 receipts. Encoded values at x536,608,680,752
  are 96 cycles, 8 injected faults, 96 allocations and 3,600 KiB peak
  requested pixel payload. Status tile at x824 must be green.
- The Python decoder rejects corrupt bits, missing ready, changes to
  every value, missing states and broken Stage251 evidence; it
  records hashes and explicit limitations.

The stress is executed once before visible gameplay, not each frame.
No benchmark comparison to a physical Switch or the original PS3
engine is implied.
