# Stage346 — native BMODEL to GPU stream-plan bridge

## Purpose

Connect the Stage345 in-memory BMODEL-to-FojRigMesh conversion to the existing CPU projection and GPU vertex-upload planning APIs. The output is a bind-pose vertex stream and a bounded texture-slot plan, not a submitted GPU draw.

## Contract

- Accepts only Stage345-integrity-ready BMODELs.
- Maps each used material to exactly one texture basename. Multi-texture materials are rejected; there is no guessed diffuse-map selection or fallback.
- Deduplicates repeated texture basenames into at most eight slots, then produces ordered triangle-soup sections and matching GPU batches.
- Reuses the existing orthographic camera projection and upload allocation planner.
- Returns only source-relative texture-name references and aggregate stream/upload metadata. The original bytes are borrowed, never copied to disk or freed by this bridge.
- Rejects overlapping buffers, insufficient capacities, invalid camera/geometry, invalid alignment and unsupported material layouts before committing outputs.

## Verification

Generated-only tests cover two sections/two textures, duplicate-texture deduplication, upload byte alignment, UV transfer, multi-texture refusal, insufficient capacity and invalid-camera transactional behavior. CI runs strict GCC/Clang C99 tests, Clang ASan/UBSan, devkitA64 compilation and a code-only owner-local audit executable.

## Limits

No texture pixels are loaded here. No deko3d command is submitted, no framebuffer is captured, no animation is applied, and no original PS3 shader/camera convention is inferred. The fixed camera in the private aggregate audit is only a projection smoke test. Actual texture upload/draw and comparison against the original game remain separate gates. All CI inputs are synthetic; original PKG/PSARC/BMODEL/DDS assets and raw captures remain owner-only.
