# Stage345 — native BMODEL-to-rig-mesh bridge

## Goal

Turn the already validated BMODEL section/material/rig view into the portable native FojRigMesh representation used by the project's existing CPU skinning research. This is an in-memory conversion; it does not create a public asset or write original geometry to disk.

## Conversion contract

- Reuses Stage343's bounded source parser and requires every section to resolve to exactly one material.
- Reuses Stage344's rig-footer and bone-index checks. Rigged meshes retain the embedded hierarchy and validated weights; unskinned static meshes are also accepted when they have the exact no-rig footer and no skin blocks or influences.
- Copies original positions, UVs, vertex normals and ordered triangle-soup sections into owned native arrays. Rigged sources additionally preserve bind-pose bone transforms and per-vertex bone/weight pairs; static sources have zero bones and zero influences.
- Retains section-to-material indices and material/texture-name offsets. Those names reference the borrowed source bytes, which must remain alive and byte-identical until the bridge object is freed.
- Rigged sources support up to the existing skinning implementation's five influences per vertex. Higher-influence layouts are rejected rather than truncated; a no-rig source with any skin block is rejected.
- Rejects unresolved/ambiguous materials, out-of-range bones, malformed/truncated input, excessive sizes, and invalid weights. The caller's output object remains unchanged on failure.
- The free function releases only bridge-owned arrays; it never frees the caller-owned original bytes.

## Verification

Synthetic-only tests cover rigged and no-rig static sources, two ordered sections, separate material/texture references, a two-bone hierarchy, exact positions/UVs/normals/weights, a bind-pose identity deformation using the existing CPU skinning implementation, ambiguous material refusal, invalid bone indices, six-influence refusal, truncation and output preservation. CI runs GCC, Clang, Clang ASan/UBSan and devkitA64 compile checks.

## Limits and privacy

This stage establishes a native data bridge, not an authentic FoJ draw. Static meshes are only a data path; they are not eligible for BANIM clips or skeletal deformation. It does not decide whether BMODEL transforms are local or global, apply BANIM tracks, select the correct animation for an actor, resolve texture basenames to private DDS payloads, submit a model draw to deko3d, or verify original-game coordinate/camera/shader conventions. Bind-pose identity is a mathematical invariant of the current skinning implementation, not proof of engine fidelity.

All public CI inputs are generated fixtures. Original PKG/PSARC/BMODEL data, raw geometry, source hashes and captures remain in owner-only storage.
