# Stage341 — owner-local original DDS sampled by the fragment shader

## Purpose and boundary

Stage340 now proves native deko3d upload and image-to-buffer readback for the selected owner-held 256×256 BGRA8 DDS in two independent NeXium executions. Stage341 is a distinct gate: the exact Stage336-uploaded image must be bound to the fragment sampler, drawn to a real NeXium framebuffer, and checked against CPU reference pixels.

The isolated opt-in target is `gpu/stage341_private_dds_frame.mk`. It does not alter the legacy NRO target. The NRO reads one bounded `sdmc:/switch/foj/gpu/source.dds`, uses Stage332/339 for strict DDS validation and base-mip RGBA8 decoding, passes the actual `dkImageLayoutGetSize/Alignment` into Stage339, uploads through Stage336, verifies the resulting copy plan, and draws a bounded inset quad with the existing research fragment shader. A fixed frame-ready marker is only a prerequisite for external capture; it is not itself framebuffer proof.

## Sampling contract

- Input: classic 256×256 BGRA8 DDS, one mip, exact expected byte length.
- Quad: clip-space bounds `[-0.82, +0.82]` on both axes; top-left UV=(0,0), bottom-right UV=(1,1).
- Filtering: linear minification/magnification, clamp-to-edge.
- Frame size: 1280×720 NeXium client window.
- Predetermined RGB sample points: (200,150), (640,150), (640,360), (640,570), and (1080,600).
- The CPU oracle uses Pillow RGBA decode and normalized bilinear sampling with texel coordinate `UV × extent − 0.5`. Per-channel RGB tolerance is 10.
- The inset quad leaves a clear-color border. The capture runner waits for two frames with different border phases to reject stale or duplicate captures while allowing the texture samples themselves to remain static.
- Screenshot alpha is not treated as authoritative because the host window capture is opaque. Stage340 independently checked all RGBA channels through native GPU image-to-buffer readback.

## Public CI and private source

Public GitHub Actions create and verify a deterministic generated-only BGRA8 DDS fixture, build the NRO/DKSH, run NeXium, capture two real shader-sampled frames, and compare predetermined pixels. Public artifacts contain only a strict aggregate JSON and the NeXium archive checksum. They must never contain original DDS/PKG files, private source hashes, decoded pixels, raw frames or guest logs.

The owner-local run uses the same NRO and gate with the original DDS from owner-only Drive. The full report, source identity, receipts, frame captures and guest logs remain in the private evidence archive. Do not reuse public synthetic proof as evidence that the original texture was sampled.

## Fail-closed acceptance

The frame gate rejects a malformed or wrong-sized DDS, source hash changes, forged frame-ready marker, missing or non-1280×720 frames, RGB samples outside tolerance, identical clear-color border phases, extra evidence files, symlinks and public export of any report not explicitly marked generated-only. It exports no raw frames or guest log.

A passing Stage341 generated-only CI proves the checker and renderer path on synthetic input. A separate owner-local Stage341 run must pass against the selected original DDS before original-texture shader/framebuffer sampling is considered proven. Physical Nintendo Switch execution, full-game rendering and gameplay remain separate gates.
