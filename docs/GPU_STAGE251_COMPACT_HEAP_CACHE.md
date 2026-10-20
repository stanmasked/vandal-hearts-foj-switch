# Stage251 — compact heap-backed synthetic base raster cache

The Stage250 opt-in scene-exact CPU cache used a fixed 1280×720×4-byte
buffer (3,686,400 bytes = 3,600 KiB) for all three resolutions. The new
Stage251 *research-only* `FOJ_STAGE251_COMPACT=1` path replaces **only
the private Stage250 scale probe's** static 3,600-KiB array with an
exact-sized heap allocation. Stage247 and Stage249 maintain their own
independent fixed-size caches; the overall guest is NOT reduced by
3,600 KiB. Normal/default Nintendo Switch NRO remains unchanged.

| Test size | Old scale-probe pixel capacity | New scale-probe requested payload | Difference |
|---|---:|---:|---:|
| 320×180 | 3,686,400 B | 230,400 B (225 KiB) | 3,456,000 B (93.75%) |
| 640×360 | 3,686,400 B | 921,600 B (900 KiB) | 2,764,800 B (75%) |
| 1280×720 | 3,686,400 B | 3,686,400 B (3,600 KiB) | 0 B |

The measured field is **requested pixel payload capacity**, not the
allocator's metadata, heap fragmentation, high-water RSS, process RAM,
GPU VRAM, Switch system usage, FPS or thermal behavior. When a
resolution changes, the previous allocation is freed before creating
the new block; allocated pixel payload has no overlap of both sizes.
Peak requested payload during the three-size sweep is 3,600 KiB.
Retaining the final 1280×720 block is expected. Lower memory use at
small resolutions is therefore a property of the reusable cache
module, not evidence of a smaller total NeXium process footprint.

## Correctness contract

- Every output is an unchanged `foj_iso_render` base raster, validated
  against both its immediate warm cached copy and an independently
  rendered uncached reference. Padding outside the active rows is
  preserved.
- Cache validity includes scene content, width and height. Semantic
  comparison avoids struct padding false invalidation. Changed terrain
  generates a miss but can reuse the same-size allocation.
- Valid cold + warm return distinct status codes. Invalid input,
  out-of-budget allocation, or malloc failure cannot report a cache
  hit. Release invalidates the cache; scene sweeps reset counters.
- Stage250 three resolutions, timings, nine genuine battle states and
  every earlier optical proof must pass in the Stage251 NRO.
- Stage251 adds optical 16-bit **payload KiB** barcodes at y44:
  x536 = 225, x608 = 900, x680 = 3600, with readiness x752.
  Corrupt, absent, saturated or incorrect payload is rejected.
- Native GCC/Clang/UBSan validates lifecycle, stride, exact size,
  scene invalidation, deterministic insufficient-budget failure and
  private status; Stage248–250 fixed-cache host tests remain mandatory.

## Limitations and integration gate

The new compact module uses `malloc` and `free` **only** for the
Stage251 test probe. It is not yet productionized for the default NRO.
Any future adoption requires physical Nintendo Switch memory budgets,
allocator fragmentation/OOM characterization and scene-change
frequency under representative workloads.

No extracted original PS3 engine, copyrighted art or resources are
used, and no real-game FPS or end-to-end performance claims are made.
