# Stage346 — native BMODEL to GPU stream-plan bridge

## Purpose

Connect the Stage345 in-memory BMODEL-to-FojRigMesh conversion to the existing CPU projection and GPU vertex-upload planning APIs. The output is a bind-pose vertex stream and a bounded texture-slot plan, not a submitted GPU draw.

## Contract

- Accepts only Stage345-integrity-ready BMODELs.
- Maps each used material to exactly one texture reference. Multi-texture materials are rejected; there is no guessed diffuse-map selection or fallback. Sections sharing the same material share a slot, but different material records keep separate slots even when their basenames match, because a basename alone does not prove that both references identify the same PSARC resource.
- Assigns one texture slot per used material record, reusing that slot when multiple sections reference the same material. Different material records retain separate slots even if their basenames match, because basename equality alone does not prove identical PSARC asset identity. At most eight used materials are supported.
- Reuses the existing orthographic camera projection and upload allocation planner.
- Returns only source-relative texture-name references and aggregate stream/upload metadata. The original bytes are borrowed, never copied to disk or freed by this bridge.
- Rejects overlapping buffers, insufficient capacities, invalid camera/geometry, invalid alignment and unsupported material layouts before committing outputs.

## Verification

Generated-only tests cover two sections/two textures, slot reuse for sections sharing one material, upload byte alignment, UV transfer, multi-texture refusal, insufficient capacity and invalid-camera transactional behavior. CI runs strict GCC/Clang C99 tests, Clang ASan/UBSan, devkitA64 compilation and a code-only owner-local audit executable.

## Limits

No texture pixels are loaded here. No deko3d command is submitted, no framebuffer is captured, no animation is applied, and no original PS3 shader/camera convention is inferred. The fixed camera in the private aggregate audit is only a projection smoke test. Actual texture upload/draw and comparison against the original game remain separate gates. All CI inputs are synthetic; original PKG/PSARC/BMODEL/DDS assets and raw captures remain owner-only.
