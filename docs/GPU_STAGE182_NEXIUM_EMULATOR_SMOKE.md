# Stage 182 — NeXium emulator guest smoke test

This stage checks **actual guest execution and screenshots** of two
independently invented Nintendo Switch research NROs in NeXium,
instead of inferring runtime from successful SDK compilation.

## Programs and input sequence

- **foj-isometric-research.nro** — synthetic 8×6 tactics with a blue
  hero and red enemy. After an initial screenshot, the CI runner uses
  the previously tested NeXium keyboard mapping (c for Switch A and
  arrow keys for D-pad) to select the hero and move the cursor right
  twice. A second screenshot must contain new gold path markers.
- **foj-coll-map-research.nro** — without the user's private COLL file,
  it must show the generated-only 50×50 fallback grid. A synthetic
  status marker and gold cursor must be visible.

Two NROs are produced in devkitPro's devkitA64 CI container. A separate
Ubuntu 26.04 runner downloads the NRO artifacts, installs a virtual X
display and Mesa Lavapipe Vulkan, downloads NeXium nightly, launches the
NROs and takes independent screenshots of both guest windows.

The SHA-256 of the downloaded nightly archive is retained in the
runtime evidence, to record exactly which mutable nightly artifact
was used. This is not a vendor signature or a permanent version pin.

## Evidence

The screenshot classifier in
tools/foj_stage182_nexium_frame_check.py requires:

1. Synthetic isometric background, blue hero and red enemy pixels.
2. Extra gold path-marker pixels following the emulated button input,
   without the blue hero disappearing.
3. Generated-only COLL background, the distinct red synthetic-data
   marker and a gold cursor.
4. Real PNG sizes; blank, missing or unchanged captures fail closed.

The workflow publishes a JSON receipt, the three PNG screenshots,
two emulator startup logs and the emulator archive digest in the
**foj-stage182-nexium-runtime-evidence** Actions artifact.

Five separate classifier regressions use invented image fixtures to
ensure that blank or stale screenshots fail. Those fixtures alone do
not qualify as emulator proof.

## Limitations

This tests guest output in **NeXium**, not performance or GPU scanout
on a physical Nintendo Switch. No original PS3 executable, commercial
assets or authentic FoJ battle rules are used. The COLL Y-toggle's
isometric screen is not yet exercised by this input sequence.
A NeXium nightly regression, Vulkan issue or changed keyboard mapping
may cause a legitimate workflow failure; do not reinterpret that as a
passing hardware test. All generated evidence must remain explicitly
labeled research-only.

Run this workflow using GitHub Actions > Stage 182 NeXium NRO guest
framebuffer smoke, or via a pull request touching its inputs.
