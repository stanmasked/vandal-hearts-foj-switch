# Stage252 — compact base-cache endurance and deterministic allocation failures

This is a private **research-only** synthetic CPU raster test for the
Nintendo Switch NRO, not a native port of the original PS3 game engine.
The ordinary game NRO, gameplay input mapping, original-resource pipeline,
and Stage251 opt-in build are unchanged.

## What is tested

One separately gated `FOJ_STAGE252_STRESS=1` experiment performs **96
sequential transitions** between 320×180, 640×360 and 1280×720 generated
raster sizes while varying cursor coordinates and one synthetic elevation.
At each transition it verifies:

- Cold raster miss and immediate warm cache hit, followed by exact
  independent uncached pixel equality.
- A deterministic injected `malloc` failure at each 13th cycle (8 events),
  followed by a successful allocation. An allocation failure must not
  return success or expose the previous buffer.
- **96 successful allocations and 96 releases**, including cleanup at the
  end of the sweep, checked as accounting counters. The test does not
  establish actual process-level leak freedom by itself.
- Requested pixel payload never exceeds **3,600 KiB**. Size accounting
  excludes allocator metadata, fragmentation, physical Switch RSS, VRAM,
  transient work buffers and earlier research probes.

The host test additionally repeats the 96-cycle workload twice and checks
allocation-failure recovery, strided bounds, and invalid optical receipt
dimensions under GCC, Clang, UBSan and AddressSanitizer/LeakSanitizer.
Deterministic injection is compiled into **only the Stage252 research
target**, never the default or Stage251 target.

## NeXium proof

The opt-in Stage252 NRO executes the stress sweep once **before the
normal visible synthetic battle**. The existing two caller-owned scratch
frames are reused. The independent barcode at **y=60** encodes:

| x origin | Optical field | Expected |
|---|---|---:|
| 536 | Completed cycles | 96 |
| 608 | Simulated allocation failures | 8 |
| 680 | Successful allocations | 96 |
| 752 | Maximum requested payload (KiB) | 3600 |
| 824 | Readiness/status tile | Green |

The decoder requires all nine genuine NeXium screenshots and strictly
inherits Stage251, Stage250, Stage249 and older rendered game-state
parity proofs. Invalid counts, a red/pending tile, modified bits, missing
screenshots or damaged inherited receipts fail closed. This tests the
instrumentation, not whole-game FPS or graphics hardware performance.

## Acceptance gates

1. C host tests and sanitizer stress are green, including injected OOM.
2. The dedicated libnx NRO builds and passes `validate_nro.py`.
3. All nine NeXium generated-gameplay states decode 96 / 8 / 96 / 3600
   and preserve the older Stage251/250 receipts.
4. Every pull request regression workflow is green before merge.
5. Do not claim measured Switch RAM reduction, new original assets,
   physical hardware validation or a complete PS3-to-Switch remake.
