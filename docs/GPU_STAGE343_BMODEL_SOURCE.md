# Stage343 — bounded native BMODEL source contract

## Purpose

Add a portable C99 parser for the verified mesh-section and material-table subset of the FoJ .bmodel format. This is a CPU-side source contract, not yet a renderer integration. Public CI uses only generated synthetic model bytes; it never opens the original PS3 package or an extracted commercial asset.

## What is checked

- The model preamble, bounded section count, per-section tags and bounded strings.
- Big-endian float32 positions, UVs, vertex normals and face normals; all floats must be finite and within explicit limits, and nonzero vertex normals must be near unit length.
- Triangle-soup vertex counts and the currently verified sequential big-endian uint16 index layout.
- Optional skin-weight tables: count consistency, finite/ranged weights, per-vertex sum-to-one, and maximum bone index. The parser reports skinning but does not apply bone transforms.
- Shape material names, the material bundle and texture basename references.
- Unique, unresolved and ambiguous shape-to-material links. Callers can require foj_stage343_materials_fully_resolved() before planning any draw; there is no fallback material.
- Output-capacity and memory-overlap checks. Failure leaves output arrays and metadata unchanged.

The output contains bounded offsets into the caller-owned source bytes instead of copying geometry or strings. The caller must keep those bytes alive and unchanged while using the plan.

## Deliberate limitations

- The trailing 0x0A/0x0C block remains opaque.
- Skeleton semantics, transforms, skinning execution, and material shader properties are not interpreted.
- Texture basename references are reported but are not resolved against a private PSARC manifest here.
- No GPU command is submitted and no model is drawn by this stage.

## Verification

tests/gpu/test_stage343_bmodel_source.c builds two synthetic sections with separate materials/textures, including one synthetic skin table. It covers section offsets, exact material mapping, ambiguous/missing material refusal, invalid indices, invalid skin weights, nonfinite geometry, truncation, capacity failure and no-partial-output guarantees. The focused workflow runs GCC, Clang, Clang ASan/UBSan and a devkitA64 compile.

## Next gate

Use the private, already archived model sample only in an owner-private run. Confirm the model's section count, skinning status and material-to-texture links without exporting raw geometry to GitHub. Only then wire a deliberately bounded, unskinned and uniquely material-resolved section into the Stage342 multi-section GPU path. Keep original model bytes, source hashes, raw captures and per-sample evidence in owner-only storage. Physical Switch and whole-game fidelity remain unverified.
