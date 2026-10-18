# Stage 187 — NeXium COLL 48-toggle guest endurance

This stage tests long-lived interaction with the **same generated-only
Nintendo Switch COLL research NRO guest** in NeXium. It is separate
from the lengthy Stage 186 cursor/zoom boundary workflow to avoid
inflating the existing runtime gate.

The Ubuntu NeXium runner starts one NRO, confirms that its process
remains alive, and delivers **48 distinct press/release events** for
Switch **Y** (NeXium's documented default keyboard key **Z**).
Actual guest-window PNGs are captured after 0, 1, 8, 9, 24, 25, 40,
41 and 48 toggles.

Two images produced by the same portable C modules used in the Switch
NRO serve as independently generated references. Each captured guest
frame must show the expected 2D heatmap / diagnostic isometric map,
the gold cursor and the red synthetic-fallback marker. The heatmap
and isometric views must be substantially different, while later
captures of the same mode must remain consistent with earlier ones.
A frozen, blank, malformed, missing or wrong-mode guest image fails.

The driver also records a host-side NeXium PID RSS snapshot and the
wall-clock epoch at all nine checkpoints, with a coarse 512 MiB
growth guard. **Host RSS is not Switch guest application memory**:
it includes emulator allocations, graphics resources and supporting
libraries. This is an early severe-growth warning, not a proof of
absence of memory leaks, console stability or stable frame rate.
A running emulator process alone is not accepted as a passing result.

Eight fixture regressions test rejection of unchanged displays, blank
frames, late corruption, malformed/missing samples and implausible
RSS claims. The genuine runtime images, two C reference PNGs, source
digest of the mutable NeXium nightly, process log, sampled RSS and
JSON audit receipt are retained in the
`foj-stage187-nexium-endurance-evidence` GitHub Actions artifact.

All assets and map values are invented. Passing this stage proves
only that the synthetic COLL homebrew remained visible and responsive
in **NeXium** over this bounded test. It does not establish a full
FoJ port, original PS3 battle rules, native Nintendo Switch hardware
operation, or performance and memory safety over longer use.
