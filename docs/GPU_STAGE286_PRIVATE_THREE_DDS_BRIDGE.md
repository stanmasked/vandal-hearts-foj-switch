# Stage286 — owner-private DDS-to-material bridge (three GPU slots)

**Dependency:** [Stage285 PR #170](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/170), exact-head [3/3 GPU CI success #39637276805](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39637276805).

## Purpose and scope

Stage285 established native deko3d GPU rendering of an **invented** three-layer FOJRM001 actor, FOJMAT01 bindings (material indices 0/1/2), and a verified U/V transparency intersection. The earlier local classic-DDS preflight handles **two** optional slots only. Stage286 adds an explicit **three-slot, no-fallback owner-local bridge** for the unchanged Stage273/275 research NRO.

This is **not** a PKG extractor, PS3 resource converter, or evidence that the original Flames of Judgment game uses DDS or FOJMAT01. The actor, UVs, camera, shader and three-material mapping remain invented. Compatible files in private `materialN.dds` slots are chosen and supplied manually.

### Supported file contract

The source directory must contain exactly the following **named required inputs** (unrelated entries are ignored, not copied or enumerated):

| Slot | Private input | Native accepted formats | Additional rule |
| --- | --- | --- | --- |
| 0 | `material0.dds` | Classic RGBA8, BGRA8, BC1/DXT1, BC3/DXT5 | Research near layer |
| 1 | `material1.dds` | Same | Research middle layer |
| 2 | `material2.dds` | **RGBA8 or BGRA8 only** | Every pixel alpha must equal 255, including all supplied mip levels |

All three DDS files must satisfy the exact C `gpu/atlas_dds.c` intake contract: bounded 128-byte classic header, dimensions 8–256, full declared mip chain, no DX10 extension or additional trailing data. Mip level 0 is currently the only level uploaded to GPU. BC1/BC3 are conservatively disallowed in opaque rear slot until decoded-block opacity has been independently bound to the private intake preflight; they remain allowed in the front/middle slots.

The source reader rejects symlinks and nonregular files, compares two bounded reads and file metadata under a pinned no-follow directory descriptor, and stops **before any output is created** if any input fails. This does not guarantee immutability against a malicious concurrent filesystem writer.

## Local-only preparation

First build the **public research NRO and DKSH shaders** using the existing devkitA64 procedure. Place owner-held, *already accessible* compatible DDS files in an ordinary local source directory. Do not upload them or a game PKG to GitHub.

Create a **new** directory in a private location; example inside the repository's gitignored `local-data/`:

```sh
python3 -m tools.foj_stage286_private_three_dds_material_bridge prepare \
  --source-dir "/owner-private/converted-dds" \
  --shaders gpu/build \
  --output-root local-data/stage286-private-sd
```

The script creates `sdmc/switch/foj/gpu/` below that root with:
- The unchanged **generated** three-layer actor (`actor.fojrm`) and generated FOJMAT01 material mapping (`actor.fojmat`).
- Exactly the **three caller-provided DDS files** placed in fixed material slots, preserving their bytes.
- Previously validated **public** DKSH shaders from `gpu/build`.
- A mode-0600 **private manifest** at `owner-private-stage286-binding.json` that pins the slot-to-DDS, shader, generated actor and material bytes by SHA-256.

All destination files are owner-local and nested under the newly created mode-0700 private root. If a step fails, only this newly created output root is cleaned up; existing source files and unrelated user files are left intact. Output under a non-gitignored tracked project path is rejected.

Verify the staged data later, before any private guest testing:

```sh
python3 -m tools.foj_stage286_private_three_dds_material_bridge verify \
  --output-root local-data/stage286-private-sd
```

The public CLI summary includes **only** the accepted slot count, file-format names and false provenance/console flags. Private paths, source hashes, pixel bytes and fingerprints are never printed. The **on-disk manifest contains actual private SHA-256 hashes** and must never be committed, attached to a CI run, placed in an issue, or shared.

**Important:** This step prepares data only. It does not launch a physical Switch or NeXium, and it does not show whether an owner-selected DDS actually corresponds to a FoJ texture or material. Any subsequent source-game comparison requires privately checked original assets and separate provenance evidence.

## Automated tests (invented assets only)

The Stage286 workflow tests:
1. Three fixed input slots, RGBA/BGRA/BC1/BC3 header compatibility and explicit opaque rear checks.
2. In-place mutation, symlink/special-file substitution, missing/malformed sources, failed-write cleanup and output no-overwrite.
3. Validation of the actual staged invented actor, FOJMAT01 material mapping, shader hash and three DDS identities.
4. Strict privacy summary, private manifest permissions and refusal to stage game-derived data into a tracked project location.
5. **DevkitA64 end-to-end preparation with genuine publicly generated DKSH** and three invented textures; verify locally on runner; never upload staged textures or manifest as CI artifacts.

Stage286 is a compatibility and **local staging** gate, not proof of PS3 file formats, proprietary texture decoding, correct game rendering, or on-device operation.
