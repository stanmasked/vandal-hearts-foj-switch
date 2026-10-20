# Stage254 — bounded reuse vs exact-sized CPU raster cache

This is a **research-only, generated-content** comparison of cache
allocation policies. It is not a Nintendo Switch memory-fragmentation
measurement, nor a port of PS3 renderer/game assets.

## Identical 384-frame workload

The native test and separate opt-in Switch NRO run Stage253's exact-sized
baseline (48 eight-frame blocks, resolution cycle 320×180 → 640×360 →
1280×720) and then Stage254's comparator with the **same scene keys**.

Both compare all active raster pixels against an independent uncached
`foj_iso_render` result, including cold and warm frames. Render results
must be identical.

| Requested pixel payload | Exact baseline capacity | Bounded reuse capacity |
|---|---:|---:|
| 320×180 (225 KiB) | 225 KiB | 900 KiB |
| 640×360 (900 KiB) | 900 KiB | 900 KiB |
| 1280×720 (3,600 KiB) | 3,600 KiB | 3,600 KiB |

The alternative holds a 900-KiB *floor* for the two smaller resolutions,
but **explicitly releases the previous large buffer** when returning from
1280×720 to 320×180. Thus the allocation high-water in this synthetic
sequence remains 3,600 KiB and no old+new simultaneous payload is held
by the compact cache. The extra live capacity at 320×180 is **675 KiB**,
and that tradeoff cannot be omitted when describing results.

## Expected counters (do not claim measured until CI passes)

| Quantity | Stage253 exact-size | Stage254 900-KiB floor |
|---|---:|---:|
| Frames | 384 | 384 |
| Cache allocations | 48 | 32 |
| Cache releases | 48 | 32 |
| Allocations avoided | — | 16 |
| Cache hits / misses | 192 / 192 | 192 / 192 |
| Peak live raster allocation | 3,600 KiB | 3,600 KiB |

A 16/48 = 33.3% reduction is a *number of cache allocation operations
in this workload*, **not** a 33.3% improvement in FPS, RAM or allocator
fragmentation. Because the floor reserves more pixels at 320×180, it
must remain research-only until workload-specific latency and memory
costs are independently measured and reviewed.

## Verification gates

GCC, Clang, UBSan and ASan/LSan run the exact-baseline comparison and
negative tests of budget rejection, stale pixels, injected malloc
failure and recovery. The sole Stage254 guest target is
`foj-isometric-compact-bounded-reuse.nro`, built with
`FOJ_STAGE254_REUSE=1`. Default and Stage251–253 NRO targets are
untouched.

At y92, six optical 16-bit values start at x536, separated by 72px,
with readiness at x968: **384/48/32/32/16/675**. The NeXium screenshot
decoder must verify nine actual guest battle states and all Stage253
and inherited Stage252–250 checks before claiming these values.

No process-wide RSS, system allocator metadata, physical Switch heap
fragmentation, end-to-end FPS, or real PS3 assets are measured here.
