# Stage344 — native BMODEL rig and skin-index validation

## Purpose

Extend the Stage343 source contract with a bounded parser for the already observed BMODEL rig footer. Cross-check each skinned section's maximum referenced bone index against the footer's bone count before any renderer is allowed to submit that section.

## Validated footer layouts

- No embedded rig: exactly one 0x0C footer byte.
- Embedded rig: 0x0A, a big-endian uint16 bone count (1–256), fixed 32-byte records, then 0x0C.
- Each record contains parent index, metadata, XYZW quaternion and XYZ translation. Parent references must be ancestral (or 0xFFFF for a root); quaternions must be finite and normalized within the established tolerance; translations must be finite and bounded.
- Footer length, tag, count, terminator and all record boundaries must match exactly.

## Skin-index policy

The parser distinguishes a structurally valid rig from skinning that is safe to use. A skinned section with no rig or with a maximum bone index greater than or equal to the rig bone count is marked out of range. The parser does not clamp, remap, or guess bone indices. Callers must require foj_stage344_skinning_bones_in_range() before any skinned draw.

## Verification

Generated-only fixtures cover valid two-bone hierarchy, a valid highest index, out-of-range indices, no-rig/static geometry, no-rig/skinned refusal, malformed parents, non-unit quaternions, invalid counts, bad terminators, inconsistent footer metadata and transactional output preservation. The workflow runs strict GCC/Clang C99 tests, Clang ASan/UBSan and devkitA64 compilation for both Stage343 and Stage344 modules.

A private-only model spot-check showed why this gate is necessary: parsing mesh/material records alone does not prove that skin weights reference existing bones. No model names, geometry, raw assets, hashes or private captures are included in public tests or artifacts.

## Limits

This stage validates rig structure and index ranges only. It does not apply bind transforms, evaluate animation tracks, establish the engine's skinning convention, bind original textures, draw a model, or prove full-game fidelity. The original PS3 package and extracted assets remain owner-only.
