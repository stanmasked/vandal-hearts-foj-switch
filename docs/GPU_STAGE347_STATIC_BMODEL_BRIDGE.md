# Stage347 — static BMODEL support in the GPU stream bridge

## Scope

Extend the existing Stage345/346 native path to accept a valid unskinned BMODEL without fabricating a skeleton. The only valid static footer is the one-byte `0x0C`; every section must be unskinned, the rig summary must report zero bones, and every vertex must have zero influences. Rigged input retains the existing hierarchy, parent, quaternion and weight checks.

The Stage346 stream plan must preserve section order and resolve each section to one material and one texture basename. The static two-section/two-material fixture is checked end-to-end through the CPU projection and GPU upload planning APIs.

## Verification

The Stage346 generated-only workflow compiles the native bridge and exercises a static two-section, two-texture source. The audit reports aggregate stream and upload metadata only. No original BMODEL bytes or texture pixels are used in CI.

## Limits

This stage still does not submit a deko3d draw, load DDS pixels or compare a real framebuffer. It only makes a static source eligible for the native stream-plan path. The original multi-section source and its texture payloads remain owner-only; the next gate is direct NRO integration and real GPU capture.
