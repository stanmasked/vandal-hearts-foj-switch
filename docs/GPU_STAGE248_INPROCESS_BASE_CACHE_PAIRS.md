# Stage248 — same-process scene-exact base-raster A/B (NeXium research)

## Question and limitations

Stage247 showed genuine warm base-raster reuse and host-visible lower terrain
phase times, but Stage246 and Stage247 ran in different NeXium processes.
Those are **not** a controlled benchmark. Stage248 compares complete generated
software battle frames with and without the scene-exact base cache in the
**same** guest, from an identical battle state, with the same output size.

This uses no original PS3 FoJ maps, art, code or renderer. Time excludes
framebuffer acquisition, graphics presentation, GPU time, COLL windows and
monitor capture. It cannot establish hardware Switch frame rates or full
game latency.

## Isolation and methodology

- Build only with explicit `FOJ_STAGE248_BASE_PAIRS=1`; both earlier stage
  profilers and the Stage247 visible base cache remain active for independent
  inherited visual evidence. The ordinary/default research NRO is unchanged.
- Two private full 1280x720 RGBA32 scratch buffers (7.03 MiB total), never the
  real display framebuffer; an independent base-cache allocation (3.52 MiB)
  and two separately warmed threat forecast caches. All are static, not stack.
- On the first frame of each exactly matching battle snapshot (including
  cursor, selection, HP, guard, map topology and overlay visibility), warm
  both presentation paths outside the timed interval; reset the 32-pair
  averaging window. A new scene reinitializes the private caches.
- Each pair uses `foj_iso_render_battle_profiled_base_cached` on both arms:
  A supplies the private base-cache object, B supplies NULL. Same code,
  same threat preview mode, same guest clock. A must return a **true cache hit**,
  not merely be configured as cached.
- Interleave AB, BA, AB, BA over successive frames. Each arm is timed with
  the libnx AArch64 system counter. Per pair, compare all 921,600 RGBA32
  pixels before accumulating times; any mismatch, cold cached arm,
  non-monotone clock or microsecond barcode saturation makes the probe fail.
- Two unsigned 16-bit average-microsecond bitfields: cached x=780, uncached
  x=852 (16 bits, stride 4, y=12). Pixel colors distinguish arms.
  x=924 is green only after 32 paired parity-checked frames, red on failure,
  amber while accumulating. Prior four phase bars start x=948 and retain
  Stage247 cache-hit proof x=1252; the modes cannot overwrite one another.
- Nine genuine frames from the established NeXium input driver are checked
  using the inherited Stage238, 241, 246 and 247 screenshot validators **plus**
  the independent Stage248 paired barcode and green parity tile. Every
  screenshot SHA-256 is retained, alongside NRO and NeXium binary hashes.
- Native GCC, Clang and UBSan tests exercise paired pixel identity, cursor
  and terrain invalidation, threat-toggle reset, output bounds, frozen clock,
  overflow failure and red telemetry.

## Reading a result

For state `s`, `uncached_mean_us[s] - cached_mean_us[s]` is a *paired
CPU software-render measurement*; positive means cached was faster for
that measured window, negative means slower. The decoder **never requires**
an artificial positive speedup. It reports active and control state medians
separately so any drift remains observable. Multiple independent NeXium
runs are still useful to quantify repeatability, not to assert real Switch
performance.

Acceptance gate: green native tests, valid devkitA64 NRO, nine genuine
NeXium snapshots with a green parity tile and both valid paired barcodes,
and unchanged inherited gameplay/phase/cache evidence. Keep Draft until
all observed CI results are green. No change to original PS3 files.
