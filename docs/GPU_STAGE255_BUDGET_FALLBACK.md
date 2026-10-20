# Stage255 — budget-aware fallback for the generated CPU-raster cache

## Scope and isolation

This is **not** the PS3 *Vandal Hearts: Flames of Judgment* renderer,
a benchmark on physical Nintendo Switch hardware, a whole-game FPS claim
or process RSS telemetry. It applies only to the generated synthetic
CPU-raster cache of Stages251–254 and is disabled unless both
`FOJ_STAGE254_REUSE=1` and `FOJ_STAGE255_BUDGET_FALLBACK=1`
are explicitly passed to the compiler. The original Stage254 build and
the default Switch NRO are unchanged.

## Problem addressed

The opt-in Stage254 policy allocates at least 900 KiB for each 320×180
frame (actual pixel payload 225 KiB), allowing that buffer to be reused
at 640×360. Consequently a budget of 225–899 KiB rejects even a 320×180
frame that would fit with exact-sized storage.

Stage255 compares the same requested frame payload with the current
cache budget and selects the requested exact size only when the preferred
900-KiB capacity exceeds that budget **but the frame itself fits**.
It is a deterministic fallback, not a new allocator or automatic system
memory monitor. Unlike the unchanged Stage254 policy, a request larger
than the budget also releases an existing reservation and invalidates
its cache entry before returning an error.

| Frame | Budget | Stage254 | Stage255 opt-in |
|---|---:|---:|---:|
| 320×180 | 224 KiB | reject | reject |
| 320×180 | 225 KiB | reject | allocate 225 KiB |
| 320×180 | 500 KiB | reject | allocate 225 KiB |
| 320×180 | 900 KiB | allocate 900 KiB | allocate 900 KiB |
| 640×360 | 500 KiB | reject | reject |
| 640×360 | 900 KiB | allocate 900 KiB | allocate 900 KiB |
| 1280×720 | 3,600 KiB | allocate 3,600 KiB | allocate 3,600 KiB |

The capacity is *pixel payload requested from malloc*, not measured
resident system memory. A 225-KiB fallback may increase allocation churn
when alternating small and medium frames; it is not unconditionally better
than Stage254 and must not be represented as such.

## Proof gates

- GCC and Clang strict C11, UBSan and Clang ASan/LSan test the Stage255
  policy across changing budget, dimensions and scene keys.
- Every successful cached result is compared byte-for-byte against
  independent `foj_iso_render` output.
- An additional 384-frame tight-budget schedule uses all 48 eight-frame
  resolution blocks with independently rendered reference pixels. It
  expects 192 hits, 192 misses, and **48** allocations (not Stage254's
  32) because each resolution block has only its exact-sized budget.
- Cases include reused low-resolution allocation, shared 900-KiB capacity,
  large-to-small shrinking, too-small budget rejection, stale-cache
  invalidation, injected allocation failure and recovery, and preservation
  of stride padding.
- The pre-existing Stage254 tests compile and run *without* the new flag,
  proving the fixed Stage254 48/32 allocation comparison remains intact.
- Compilation with Stage255 enabled alone must fail explicitly.
- The Stage254 NeXium workflow is independently triggered by edits to
  `core/base_cache_compact.c`, but that guest job executes the **old**
  Stage254 flag configuration. Passing it does not constitute direct
  NeXium proof of the Stage255 policy.

## Separate opt-in Switch NRO and NeXium receipt

A new isolated target `build/foj-isometric-compact-budget-fallback.nro`
is compiled with both Stage254/Stage255 flags. Earlier targets and the
normal NRO continue to omit Stage255.

The Stage255 probe performs 384 synthetic CPU-raster frames, cycling
320×180, 640×360 and 1280×720 for 48 eight-frame blocks, with a budget
equal to each block's exact pixel payload. It renders every frame against
an independent uncached raster reference. The additional optical
receipt at guest y108 (six 16-bit fields beginning at x536, readiness at
x968) is intended to encode **384 / 48 / 48 / 192 / 192 / 16**:
frames, allocations, releases, hits, misses and 320×180 fallback blocks.

This deliberately exhibits **48** allocations under tight budgets,
rather than Stage254's **32** when 900-KiB capacity is affordable.
The Stage254 receipt remains at y92 and continues to report
384/48/32/32/16/675 in the same guest run.

`tools/foj_stage255_budget_guest_check.py` verifies nine fresh NeXium
battle-state screenshots, its six counters, the green readiness tile
and the complete Stage254 + ancestor receipt chain. Mutation tests
reject corrupted values and missing predecessor evidence.

## Completion gates — not yet confirmed

- [ ] Strict GCC/Clang/UBSan/ASan/LSan host tests
- [ ] Independently compiled and validated research-only devkitA64 NRO
- [ ] Nine genuine NeXium screenshots with Stage255 optical receipt
- [ ] Stage254's inherited receipt on the same nine screenshots
- [ ] All repository-wide PR workflows green on the same head commit

No claims about process RSS, Switch GPU frame times, physical console
performance or gameplay from the original PS3 game are made.
