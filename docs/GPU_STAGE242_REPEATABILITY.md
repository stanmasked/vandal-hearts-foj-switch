# Stage242 — independent NeXium render-timer repeatability

Stage241 [PR #125](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/125)
already decoded and archived nine guest-render timing values from an actual
Switch research NRO in NeXium. That run had a 32-render-sample block average
per captured scene, with a single-run range of 8,485–8,920 microseconds.
A previous successful NeXium execution had approximately 3.8–4.2 ms values.
This between-run difference cannot be interpreted as a software regression,
improvement, or real Switch frame rate without repeatability controls.

## Independent experiment

The Stage242 workflow compiles **one generated-only isometric NRO** and then
launches **three different NeXium processes**, each on its own GitHub Actions
runner. Each process receives the same scripted A, directional input, right
stick, B, ZR and Y input sequence and captures nine genuine GUI screenshots.
Each repeat uses Stage241's verified 16-bit decoder and Stage238's independent
cache-state/battle transition proof; it separately uploads its nine images,
guest log, decode receipt and both binary SHA-256 digests.

A downstream aggregator downloads all three run artifacts and fails closed
unless it can independently re-decode the same 27 PNGs, reproduce receipt
values and SHA-256 hashes, and verify the exact *same NRO binary* and *same
NeXium archive binary* were used. Duplicating an entire nine-frame image
set between separate runs is rejected. Differences in time samples alone
are not sufficient proof that a new emulator process actually ran.

The tool outputs: the nine scene values per guest, median duration of each
nine-scene set, median of these three medians, absolute run-median spread,
relative spread as a percentage of the three-median median, and population
coefficient of variation across the three guest medians. Measurements are
rounded only in display metrics (percentage to three decimals), not raw
microseconds. The report preserves binary hashes and the explicit absence of
hardware, FPS, GPU or end-to-end latency measurements.

No arbitrary allowed-variation threshold is applied: repeatability may
genuinely be poor on shared runners. A large spread must be *reported*, not
discarded to make an optimization look good. Three launches and nine
scripted scenes per launch are not enough to construct device-level
performance confidence intervals.

## Interpretation and exclusions

The value in each captured NeXium frame is the most recently completed
**32-frame mean CPU software-render duration** measured inside an emulated
Switch NRO via `armGetSystemTick` and `armTicksToNs`. These 27 recorded
means are *not 27 independent individual frame times*, and screenshots
are different battle states rather than a controlled GPU benchmark.
An emulator clock is not physical Nintendo Switch hardware clock time.

The measurement excludes framebuffer presentation, host NeXium UI, GPU,
vsync, audio, controller handling and any original PS3 FoJ game renderer.
The code base remains a synthetic 8×6 tactical research prototype.
No copyrighted original PS3 assets are committed or uploaded.
