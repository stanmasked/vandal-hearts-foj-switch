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

## Pending before completion

The Stage255 policy has only an isolated native CI target. It has not
been wired into an experimental NRO or proven in NeXium. Do not
promote it to a default build or claim emulated/physical-console
performance gains based on these host-only tests.
