# Stage312 — horizontal BC1 cross-page gutter rendered by real NeXium GPU

**Base:** Stage311 [PR #196](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/196), four green native C checks (GCC, Clang, UBSan, ASan/UBSan). Stage310 already verified eight vertical BC1 seam color pairs in genuine NeXium guest GPU frames. Stage312 rotates the experimental reconstruction to the **horizontal** boundary.

## Isolated opt-in GPU experiment

An invented 1024×1024 BC1 DDS is built in native code and decoded using the actual Stage301 C page decoder. It contains eight 32px-wide column bands in two vertically adjacent pages: upper page (1,1) and lower page (1,2). No actual NPEB00148 bytes or real game texture source is read.

The native Stage311 horizontal generator copies for each of 256 columns the last texel row of page (1,1) into 128 rows of a third 256×256 RGBA8 material and the first texel row of page (1,2) into the other 128 rows. Every column must have a contrasting pair and a nontrivial bilinear midpoint. The existing Stage309 18-vertex research scene now has a second **opt-in** geometry orientation:

- Upper original page material 2: full X range from −0.6 to +0.6; screen Y from 0 to +0.5; constant local V=0.5.
- Lower original page material 1: full X range, screen Y from −0.5 to 0; V=0.5.
- Foreground horizontal seam material 0: screen Y from −0.03 to +0.03, full X range; image V interpolates across the two gutter texel centers, while U runs across the eight different stripe colors.
- The existing reverse-Z Greater depth convention is preserved: both original pages z=0.55, foreground gutter z=0.68. Explicit `DkFilter_Linear` is enabled in the opt-in NRO only.

The scene retains strict generated-only Stage293 source intake. The native NRO writes its own `FOJ_NATIVE_STAGE312_HORIZONTAL_GUTTER_V1` marker with 256 columns and 8 contrast pairs. Previous Stage309/310 NRO binaries are unchanged.

## Proof gates

GCC and Clang compile and execute both an independent Stage312 native scene test and the actual Stage311 256-column synthetic BC1 reference. The guest NRO is compiled by devkitA64, along with generated UAM shaders. The real NeXium test must capture two distinguishable 1280×720 GPU frames **after** source attestations and native guest startup.

For each of eight X locations approximately at 315, 407, 500, 592, 685, 777, 870, and 962 pixels, the independent screenshot verifier requires the expected upper RGB color near screen Y=280, expected lower color at Y=460, and a strictly intermediate RGB near Y=360. The upper/lower 7×7 regions must match ≥45/49 pixels, middle 7×5 ≥33/35, plus individual tests rejecting a clamp-to-edge endpoint leak near the seam. Those are expected capture coordinates based on prior real deko3d viewport observations, not proof until NeXium actually completes.

The Python host-generated PNG tests are **only negative regressions**; successful host mocks never count as emulator evidence. True positive GPU status requires two real NeXium frames, strict native marker, identity of Stage293 synthetic DDS source before/after the guest run, and a privacy-safe eight-file public allowlist. No raw guest log or private PS3 files are uploaded.

## Scope limits

This demonstrates one explicit CPU-assembled horizontal gutter rendered with GPU linear interpolation. It does **not** prove automatic bilinear reconstruction between independently bound page textures, arbitrary original FoJ geometry/UV topology, rotation/resizing for non-square pages, or operation on physical Nintendo Switch hardware. The next research step is generalized arbitrary-direction geometry crossings after private validation of actual game UV mapping.


## First-frame stall diagnostics (CI-only)

The Stage312-specific NRO entry point wraps the first guest input/acquire/submit/present sequence with a bounded fixed-code progress file. It records only `FOJ312P1 phase=0..7`, never paths, assets, pixels, shader bytes, or raw guest output. The failure handler prints only the last validated phase and the existing numeric boot-journal record; the progress file and raw `guest.log` are not published. Phase 0/1 brackets first `padUpdate`, 2/3 brackets first swapchain image acquire, 4/5 brackets first frame command submission, and 6/7 brackets first presentation. The existing independent eight-band screenshot/color audit remains mandatory and unchanged.


## Stage312-only twelve-frame boot-status warmup

An actual NeXium job reached the first swapchain presentation (`FOJ312P1 phase=7`)
but did not reach the required eight-band texture image within its observation
window. The first presentation is **not** texture evidence: the inherited
three-material path normally shows 120 diagnostic status frames **per slot**,
or 360 flat-color frames, before submitting the textured scene.

The Stage312-only entry point now includes the original status enum before
locally substituting four frames per slot (12 total). All three DDS status
screens still render, but the textured scene is submitted much earlier.
Other research NROs keep their original 120-frames-per-slot behavior.
The independent eight-band / two-frame color audits, source attestations,
native receipt and eight-file privacy allowlist are unchanged. Success
is not claimed until a real NeXium capture passes the original checks.
