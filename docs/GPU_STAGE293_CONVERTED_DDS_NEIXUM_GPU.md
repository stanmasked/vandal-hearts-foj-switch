# Stage293 — actual NeXium GPU proof of three Stage292-converted textures

**Stack:** Stage292 [PR #177](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/177), Stage291 #176, Stage290 #175, Stage289 #174, Stage288 #173.

## What is new

Stage288 already proved that three generated RGBA DDS textures, staged by Stage286, reach NeXium's real Vulkan GPU. Stage292 proved an invented BGRA8/GTF-like to DDS conversion against the real `foj_atlas_dds_decode` C11 loader.

Stage293 closes the gap by feeding **three actual Stage292-converted DDS outputs** (not Stage288's direct `generated_dds` fallback) through Stage286 and the existing alpha-capable deko3d NRO on NeXium. The additional Stage292 constant-color fixture mode is explicitly tagged, deterministic and checked against complete source bytes. The near, middle and opaque rear use public invented colors identical to the previously validated Stage288 screenshot probes. The DDS headers differ from Stage288's original direct generator (explicit mip level 1), allowing proof that the converter path was used.

## Acceptance

- Public fixture sources are generated in memory by `generate_solid_fixture` with the unique Stage292 synthetic tag and exact full-data verification.
- `convert_fixture` converts BGRA to strict RGBA DDS, checks native DDS format and preserves alpha; Stage293 refuses fallback identical to Stage288's direct `generated_dds`.
- The exact three converted outputs are staged through real Stage286 `prepare/verify`, with the private receipt in ephemeral runner temp.
- SHA-256 of the *known public synthetic constants* and byte-for-byte DDS identity are checked **before** and **after** the guest. No owner's real source paths, hashes or private bytes are emitted.
- Real NRO in NeXium renders two different 1280×720 GPU frames. Existing pixel probe checks verify two independent overlap points and one opaque rear-only point plus a clear-color phase change; native NRO writes correct material sort/blend/depth receipts.
- The independent Stage293 auditor re-checks all receipts and frames. Publication uses Stage289's strict file/tree checks and a new exact **nine-file** allowlist; neither raw `guest.log` nor the Stage286 binding manifest is uploaded. Failure uploads nothing.
- CI host negative tests reject altered converted hashes, changed pixels, missing native receipts, duplicate images, unexpected private files, symlinks and publication spoofing.

## Limits

This proves only the chain **invented BGRA → Stage292 converter → Stage286 DDS staging → native Switch NRO → NeXium GPU screenshot**. It does not prove the true NPEB00148 source format, RSX swizzle, original game material mapping, an original texture conversion or a physical Nintendo Switch GPU. All game assets stay outside public GitHub.
