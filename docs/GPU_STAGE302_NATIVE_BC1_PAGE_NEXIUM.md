# Stage302 — prove C-decoded synthetic BC1 1024 atlas page in real NeXium

Stage301 [PR #186](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/186) established that all 16 independently decoded 256×256 BC1 pages from a generated 1024×1024 DDS match the old full-size C decoder. Stage302 connects that actual C decoder to the **native deko3d GPU material upload and real NeXium captured frames**.

## Generated-only native path

An opt-in `gpu/stage302_generated_page.mk` builds a distinct NRO enabling `FOJ_GPU_STAGE302_GENERATED_PAGE_PROBE`, leaving the normal Stage275 research NRO unchanged. It first reads the three *generated* Stage292/293 DDS fixtures through Stage286 and validates **every RGBA pixel** of all three as exactly the expected public synthetic constants (64×64 RGBA fixtures). Any unknown, malformed or changed input fails **before GPU device creation**.

Then the native C `foj_stage302_apply_generated_page()` creates a new, invented 1024×1024 classic BC1 atlas in RAM. One selected 256×256 page at `(2,1)` contains the quantized cool RGB **(24,203,222)**; all other pages are bright red. The module calls the **actual Stage301** `foj_bc1_1024_decode_page()`, validates every returned pixel is correct and replaces only the rear material's decoded RGBA buffer and 256×256 metadata. Nothing is read from a game PKG.

The NRO independently writes a new exclusive guest receipt `FOJ_NATIVE_STAGE302_PAGE_V1 p=2,1 rgb=24,203,222 size=256` before GPU boot. This marker alone is only proof of native CPU execution; it is **not** proof of GPU rendering.

The existing Stage273/274 NeXium driver then waits for the *actual GPU* framebuffer overlap and opaque-rear probes, captures **two nonidentical 1280×720 screenshots**, verifies the native sorting/blending/depth receipts, and tests the rear-only material region against the precisely quantized BC1 page RGB within **±2**, tighter than the original direct-DDS color difference, explicitly rejecting a fallback to the previous `(21,202,219)` rear color. Stage302 checks identical material footprints across two different GPU clear-color phases.

## Acceptance

- Native host GCC/Clang compile and exercise the actual Stage302 generated-source guard: accepts only exact three known RGBA fixtures, rejects modified input, missing pointers and incorrect texture metadata; no original texture access.
- devkitA64 builds an opt-in NRO containing the Stage301 C decoder and Stage302 page generator.
- Real NeXium rendering contains the pixel result of the selected page; independent audit compares all three material probes, native receipts and source fingerprints before and after the guest.
- Only an audited exact allowlist of **ten** generated-only files including 2 guest PNG frames and the NeXium archive SHA256 is published. No raw guest log, owner manifest, unknown DDS or original game file can enter artifacts.
- Every test output explicitly distinguishes original FoJ material/texture provenance, physical Switch execution and emulator GPU capture.

## Limits

A color probe in a flat generated page is a deliberate first end-to-end acceptance test. It does not yet prove continuous UV coordinate mapping across page boundaries or that a large original FoJ atlas is accepted without header differences. The source's 1024 compressed bytes are synthesized by **our guest C function**; the actual user-owned NPEB00148 DDS images are not re-read or uploaded. The NRO does not load an external 1024 image. Future work should validate page selection at multiple UV samples and carefully integrate only privately authorized real source textures.
