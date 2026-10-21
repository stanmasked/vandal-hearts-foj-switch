# Stage301 — bounded BC1 1024×1024 to 256×256 atlas pages

**Base:** [Stage300 Draft PR #185](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/185). Historical evidence in [REAL_RESOURCE_SIGNATURES.md](REAL_RESOURCE_SIGNATURES.md) established that one of five sampled original `.tga`-named assets is a classic BC1/DXT1 DDS with dimension 1024×1024, size 524,416 bytes. Stage300 reconfirmed this *dimension/format gap* using synthetic data and both actual native C decoders.

## Change

Stage301 introduces an **opt-in C research API** `foj_bc1_1024_decode_page()` in `gpu/bc1_atlas_page.c` and `.h`. It does not loosen `foj_atlas_dds_decode()`, change its 256px limit, or accept unknown GTF/RSX textures. The source is a caller-owned in-memory DDS. No file-system paths, extraction or new upload endpoints are introduced.

Only a **single-level classic DDS DXT1** with a *strict* 1024×1024 header, 524,288 bytes of compressed payload, exactly 524,416 bytes total, canonical flags/caps and no trailing bytes is accepted. No DX10, cube, volume, mip tails, BGRA, BC3, swizzle or unverified game-specific layouts. Historical original source header flags have not been reread in this stage, so they might differ.

For a requested integer page coordinate `(page_x,page_y)` in a 4×4 grid, the helper copies **only its BC1 blocks** into a canonical synthetic 256×256 compressed DDS envelope, then calls the **existing actual C `foj_atlas_dds_decode()`** to decode RGBA pixels. It neither constructs a 4 MiB full RGBA atlas nor alters existing GPU texture limits.

| Allocation | Bytes | Description |
| --- | ---: | --- |
| Caller-owned original-size BC1 DDS buffer | 524,416 | Already compressed; unchanged |
| Temporary canonical 256×256 BC1 DDS | 32,896 | Allocated and freed by helper |
| Caller-owned one-page RGBA8 output | 262,144 | Existing GPU atlas maximum |
| Sum of these explicitly counted buffers | **819,456** | ≈ 800 KiB, *not* a measured runtime peak or actual GPU budget |
| Legacy full 1024×1024 RGBA8 output alone | 4,194,304 | 4 MiB |

A 1024px atlas has sixteen 256px pages. The API refuses out-of-range coordinates, incorrect header, wrong compressed byte count, mip flags, insufficient output capacity, null arguments and trailing data, preserving output buffer and metadata on every validation failure. It also relies on the strict atlas decoder to refuse any downstream unsupported DDS.

## Verification, separated from claims about original game data

GitHub Actions compiles the real legacy `core/dds_texture.c` and current `gpu/atlas_dds.c` **with the new BC1 page helper** on GCC and Clang. For public generated-only BC1 blocks whose color palette and per-pixel indices vary spatially, the test decodes the full 1024 image with legacy C and **all 16 pages** with the strict C loader. It compares every RGBA pixel in every page to the corresponding full-image reference, including the BC1 three-color transparency case. Additional negative tests prove strict bounds, flags and no writes after rejection.

The helper is also included as a build input in `gpu/topology_reject_contract.mk` and compiled with the existing research NRO by devkitA64. **This does not imply the NRO actually calls the page helper, uploads the decoded result to deko3d or draws an original FoJ texture.** It establishes native compilation compatibility and CPU decoder parity, not GPU presentation or physical hardware behavior.

No user-owned PS3 PKG, actual game DDS pixels, local source paths, SHA-256, preview images or NRO binaries are uploaded to public CI. The only source input in this stage is a deterministic, invented BC1 pattern matching an already published width/height/format/byte count.

## Next

Stage302 should add an explicit, generated-only NeXium guest scene that loads **a selected page generated through this new actual decoder** and validates GPU upload/rendering and UV/page mapping. For original FoJ resources, first confirm the owner's actual DDS header/caps locally; then validate the decoded source only in an authorized private environment, without publishing commercial game assets.
