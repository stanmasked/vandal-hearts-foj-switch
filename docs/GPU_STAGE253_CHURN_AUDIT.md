# Stage253 — sustained cache churn and pixel-payload high-water audit

This stage extends the completed Stage252 research **without changing the
normal Nintendo Switch build**. It uses generated-only 8×6 isometric
terrain; no PS3 resources or original gameplay are involved.

## Workload

In one opt-in guest process, immediately after the Stage252 fault
recovery experiment, Stage253 executes **384 independent CPU frame
checks**, divided into **48 blocks of eight frames**. Resolution advances
320×180 → 640×360 → 1280×720 at every block. Each eight-frame
block has four distinct generated cursor/terrain scene keys with one
immediate repeat per scene.

| Counter | Expected |
|---|---:|
| Frames | 384 |
| Size-changing allocations | 48 |
| Matched releases, including final cleanup | 48 |
| New-scene raster cache misses | 192 |
| Same-scene cached hits | 192 |
| Maximum live requested pixel payload | 3,600 KiB |

Every output is compared byte for byte against a freshly rendered
uncached reference; a repeat may not trigger a new allocation. The
test also checks each allocation is exact-size and that after explicit
cleanup the cache has no live buffer. GCC, Clang, UBSan and Clang
ASan/LSan independently run a repeated stress-test workload.

## Measurement scope

**Important:** these are counters from the compact cache itself:
requested pixel-buffer capacity, number of allocations/free calls,
cache hits, misses and correctness of active pixels. The workflow does
**not** measure host allocator internals (free-list fragmentation,
allocator metadata, address-space fragmentation, resident set size,
Nintendo Switch system-memory limits, actual GPU memory, temperature,
or game-wide FPS).

A low number of allocations inside same-resolution blocks demonstrates
reduced *requested allocation churn for this synthetic workload*. It
does not prove a percentage of system RAM saved or a reduction in
physical fragmentation.

The y76 optical receipt encodes, in order, 384/48/48/192/192/3600
with 16-bit bars beginning at x536 and ending with a readiness tile
at x968. The image decoder must first validate **all** Stage252
receipts, nine real emulator screenshots and their original
Stage251/250 proof chain. A modified bit, count or missing readiness
tile must fail closed.

## Boundaries

Stage253 is gated behind `FOJ_STAGE253_CHURN=1` and is present only
in `foj-isometric-compact-cache-churn.nro`. The default game guest
and older Stage252 guest are unaffected. Tests must pass native
compilers, sanitizer runs, devkitA64 build, NeXium, and the full
regression matrix before merging the PR. Do not claim performance
improvements on physical Nintendo Switch until tested there.
