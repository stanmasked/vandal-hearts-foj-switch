# Stage250 — CPU base-raster cache size scaling, cold refills and RAM

## Scope and provenance

This test uses **only our generated 8×6 battle map** with the original
CPU software rasterizer. Stage247's actual on-screen research framebuffer
and gameplay are not modified. No assets from the PS3 PKG are loaded.
The experimental build gate is `FOJ_STAGE250_SCALE=1`; default NRO
targets and earlier experiment targets remain unchanged.

## Three tested output resolutions

| Raster resolution | Active RGBA32 bytes | Full-size reserved private cache |
|---|---:|---:|
| 320×180 | 230,400 | 3,686,400 bytes |
| 640×360 | 921,600 | 3,686,400 bytes |
| 1280×720 | 3,686,400 | 3,686,400 bytes |

Each *scene change* triggers three distinct measurements in a single
NeXium guest. Every resolution does one real **cold miss** after
dimension invalidation followed by one **warm hit**, with both separately
timed. Both output buffers must be byte-for-byte equal. An entirely
independent uncached `foj_iso_render` executes after the timed region
and must reproduce the exact pixels. Cache miss/hit counts must be 3/3,
bypasses 0. Subsequent frames of an unchanged scene perform no further
Stage250 scaling work; changes in scene or threat-preview visibility
trigger a complete new sweep.

Two private 1280×720 scratch frames are reused from Stage249. Stage250
adds one max-size cache (~3.52 MiB). Named opt-in allocations are bounded
to **21 MiB** by static compile assertions; this excludes the Switch
framebuffer and other engine memory and is *not* a measurement of total
resident RAM. The cache reserves 1280×720 space even at 320×180; this
waste is a design cost, not optimization.

## Optical proof in NeXium

New 16-bit base-only CPU timings at framebuffer y=28:

- x536 and 608: cold / warm 320×180.
- x680 and 752: cold / warm 640×360.
- x824 and 896: cold / warm 1280×720.
- x968: green readiness and exact-pixel parity tile.

Decode nine *actual* NeXium battle screenshots, retaining inherited
Stage249 (≥3×32 matched AB/BA windows), 248 parity, 247 reuse,
246 phases and Stage238/241 gameplay/timing proofs. Reject missing,
saturated, corrupted, or duplicate receipts.

A **modeled** 32-repeat comparison assumes the next 31 base renders
would take the same time as the first cold call. This illustrates possible
amortization, not observed frame rate, event frequency, or actual
end-to-end advantage. A scene changing every frame has no warm reuse.
Cache feasibility must ultimately depend on a measured real-world
scene invalidation frequency and physical hardware budgets.

## Gates

GCC, Clang and UBSan tests (including 320/640/1280,
scene invalidation, dimensions, parity, synthetic clock failures and
memory bounds), separate devkitA64 research NRO, negative Python decoder
tests and genuine nine-state NeXium run. Preserve NRO SHA-256, NeXium
archive hash, optical screenshots and JSON evidence.

Not a physical Switch FPS/GPU benchmark or original PS3 engine port.
