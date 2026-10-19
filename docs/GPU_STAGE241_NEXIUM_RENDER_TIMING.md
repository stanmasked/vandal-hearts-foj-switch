# Stage241 — read software-render microseconds from real NeXium screenshots

Stage240 [PR #124](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/124)
merged with 17/17 green workflows. Its generated-only NRO takes a libnx
AArch64 system-tick measurement around *only*
`foj_iso_render_battle_cached_options`, averages 32 recent software-render
samples, and paints 16 low-bit-first microsecond bits onto the framebuffer.

## Evidence used to design the decoder

The previously successful Stage238 NeXium screenshot artifact from
[workflow run 39183860145](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39183860145)
contains actual Stage240 guest pixels. Inspection of nine 1280×720
captures confirmed the 16 timing-bar centers in the scaled NeXium GUI:
x = 440,444,448,452,456,460,464,467,471,475,479,483,487,491,495,499.
Each bar is checked at rows y=13,15,17. The AArch64 framebuffer's
little-endian RGBA color is rendered as RGB in NeXium:
on=(255,232,127), off=(48,37,48), not-ready=(63,134,184).
Reading the nearest untrusted GUI pixels or the entire image histogram
would be unsafe; samples are bounded to these exact verified positions.

The nine historical captures decode (microseconds):
initial 3875; selected 4162; hovered 3841; hidden 3879; restored
4027; cancelled 3965; guarded 3849; guard-hovered 3905; ended 3884.
These are **32-frame rolling-block mean durations** of the portable,
generated research **CPU software renderer** measured inside a NeXium
guest. They are not the time taken to present a full frame or a true FPS
measurement, and were not measured on physical Nintendo Switch hardware.

## Stage241 automated proof

`tools/foj_stage241_render_guest_check.py` decodes nine fresh guest
screenshots. It requires the Stage238 *independent* cache state/turn
verification on the exact same images. Each of the 16 RGB bits must
match at all three sample rows; pending, corrupt, zero and saturated
0xffff timings are rejected rather than silently assigned values.
The checker also requires at least two different measured values and
different frame content, and records SHA-256 of each evidence file.

`.github/workflows/stage241-nexium-render-timing.yml` builds the real
generated Switch NRO, drives actual A / D-pad / RStick / B / ZR / Y
NeXium inputs, captures nine frames, decodes the timings, and uploads
screenshots plus an asset-free JSON receipt. Synthetic regression
cases reject fake GUI colors, wrong bar offsets, blank or missing
frames, corrupted bits, incorrect cache transitions and stale timing.

The timing source covers only CPU-side isometric rasterization.
Excluded: framebuffer acquire/present, COLL overlays, input handling,
NeXium GUI itself, GPU execution, vsync and host-side wall-clock time.
No original PS3 game resources, code or AI enter these measurements.
This is not yet a playable PS3 game port or real Switch performance data.
