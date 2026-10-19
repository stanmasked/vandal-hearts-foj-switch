# Stage246 — exclusive four-stage CPU rendering cost (NeXium)

After Stage245 [merged PR #129](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/129)
measured ~4% lower duration for the cached **full software rasterizer**
in selected synthetic battle scenes, this stage identifies where the
function actually spends its CPU time.

## Exclusively measured phases

The existing generated `foj_iso_render_battle_cached_options` uses one
shared rendering implementation. Its new optional profiler samples the
*same monotonic guest AArch64 nanosecond clock* at five boundaries:

1. `terrain_ns`: prepare FojDemo/map, fill full 1280x720 background, draw
   generated 8×6 terrain, figures, selection and route.
2. `threat_compute_ns`: invoke cached or uncached simulated movement
   danger matrix, including the conditional check when unavailable.
3. `threat_paint_ns`: render risk marks and predicted enemy landing tab
   when a danger matrix exists.
4. `battle_hud_ns`: health bars, move/guard indicators, attack forecast,
   enemy route, and win/defeat bar.

The four measured durations **partition one complete CPU function call**
without overlap: the sum equals `whole_raster_ns` *before per-phase
microsecond rounding*. The initial/hidden/cancelled/ended game scenes
are important no-active-forecast controls. Boundary clock-call overhead
is included in the measured groups, rather than silently subtracted.

The **normal NRO remains uninstrumented**: the public production API
delegates to the same rasterizer with a NULL timing callback and NULL
receipt. Only `build/foj-isometric-phase-report.nro` compiles with
`FOJ_STAGE246_PHASE_TIMING=1` and paints four 16-bit microsecond bars
and a validity status tile, disjoint from all previous guest telemetry.
The protocol batches 32 consecutive image frames. Native GCC,
Clang, UBSan and adversarial guest PNG controls require exact phase
accounting, untouched synthetic gameplay pixels, zero extra clock
calls in the uninstrumented API, fail-closed clock and arithmetic checks,
and correct color decoding.

### Validity of scene-scoped 32-frame means

The optional Stage246 guest explicitly **resets the phase accumulator
on every real battle input and threat-overlay visibility toggle**,
before the first render of the new state. Until a fresh window of 32
valid frames completes, the barcode stays in pending mode; an older
READY value cannot be misread as the timing for a new scene. A native
regression checks that partial windows and previous averages are
discarded when a new scene begins.

Counter timestamps for an *empty* phase (for example, hidden threat
markers) may legitimately be equal at the timer's tick resolution.
Timestamp boundaries therefore must be nondecreasing, with a strictly
positive overall render duration; reversals or a frozen entire render
fail closed. Extra native controls test both cases.

The GitHub Actions experiment uses the tested Stage245 NeXium control
sequence with generous accumulation time, produces nine real GUI PNGs
and decodes four phase costs for each named game state. Stage238
battle-cache audit and Stage241 render timer must independently pass
against the **same** nine captured images. Frame SHA-256, guest NRO
SHA-256, NeXium archive SHA-256, and guest logs are retained.

## Hard interpretation limits

These are CPU software-rasterizer phases on an **original generated
8×6 tactical research scene** — NOT the original PS3 FoJ executable,
original game assets, GPU timing, Vulkan draw calls, controller response,
audio, buffer acquisition, VSync, actual frame latency, physical Switch
or video-game FPS.

Even if forecasting is much more expensive without a cache, no overall
game-speed or physical console performance claim can be made from this
trace. Four phase means are each rounded down independently, so their
sum may differ from the independently rounded total by at most 3 µs.
Measurements are best used to prioritize targeted software profiling
and correctness work.
