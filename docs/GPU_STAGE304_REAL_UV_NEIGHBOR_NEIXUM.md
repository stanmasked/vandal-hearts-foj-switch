# Stage304 — real NeXium GPU selects adjacent BC1 pages across u=0.5

**Base:** [Stage303 PR #188](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/188), whose actual GCC/Clang × Python 3.11/3.13 CPU matrix confirmed 80/80 synthetic seam tests. [Stage302 PR #187](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/187) independently confirmed a real NeXium guest displayed one C-decoded BC1 page (two framebuffer screenshots, 121/121 correct pixels each).

## Purpose and honesty boundary

Stage303 proved nearest UV routing works on CPU. Stage304 uses the **actual same C resolver and native C BC1 decoder inside two distinct opt-in NRO builds**, and requires GPU frames from each. It shows that selecting a page immediately on either side of one UV boundary results in the appropriate GPU material pixels.

**This is a two-run neighbor-page selection test, not yet a single textured polygon crossing the seam in one framebuffer.** Neither geometry splitting nor bilinear filtering across the page boundary is implemented. It does **not** verify any original FoJ UV metadata, original texture assets or physical Switch hardware.

## Input identity and native selection

The NRO refuses anything except the exact three known Stage292/293 invented DDS material inputs. Every pixel and relevant metadata are validated before generating the 1024×1024 BC1 input. A different, untrusted material file is not accepted even if its filename looks right.

The native Stage303 `foj_bc1_1024_resolve_uv` resolves two adjacent texel centers in the 1024-wide atlas:

| Case | Atlas UV u | Atlas texel | BC1 page | Local page texel x | BC1 RGB565 | Decoded RGBA |
|---|---|---:|---|---:|---|---|
| Left | 511.5 / 1024 | 511 | (1,1) | 255 | 0x163A | (16,199,214,255) |
| Right | 512.5 / 1024 | 512 | (2,1) | 0 | 0x1E5B | (24,203,222,255) |

The v coordinate is 384.5/1024, selecting page y=1 and local texel y=128. The generated C input colors *all pixels of the two pages* differently, and colors every other page pure red. Therefore choosing the wrong page is visible, not a silent green test. Both selected colors remain within the prior Stage273 wide COOL tolerance, but the **Stage304 independent frame probe uses tolerance ±2**, so it cannot confuse either selected page or the old COOL fallback with the other one.

Each NRO validates its complete 256×256 C-decoded page pixel-by-pixel and replaces **only the rear RGBA material**, which the existing verified deko3d upload path then transfers to the guest GPU. It writes an exclusive, exact native marker (page, local x/y and expected quantized RGB). A marker by itself is **not GPU proof**.

## Verification

The new Stage304 CI builds two research NROs with devkitA64 using independent defines `STAGE304_SIDE=0` / `1`. Native C host GCC and Clang validate both modes as well as malformed and modified inputs, unknown side, null args and no output mutation on refusal. Python mocks test the audit/publish controls, but mock PNGs are never accepted as a real NeXium run.

The actual NeXium steps (one per side) each:
1. Prepare exactly three Stage293 generated DDS inputs via Stage286.
2. Execute the actual side-specific NRO and the existing Stage274 drive under Mesa/Vulkan, capture two genuinely rendered 1280×720 GPU frames, and confirm native sort/alpha/depth receipts.
3. Independently revalidate before/after synthetic DDS identity, native side marker and rear-only RGB probes (at least 116/121 matching pixels, tolerance ±2 on each color channel) for **both** frames.
4. Publish only ten allowlisted evidence files per side (no raw guest log, source/private manifest, original package, source pixels or DDS).

A final **compare** job independently downloads those two vetted public evidence packages and checks the identity/expected color of each, the refusal of the opposite color and nonidentical GPU frames between the left/right runs. Only then can we claim GPU neighbor-page selection at this boundary.

## Next evidence gate

A future Stage305 can construct a **single screen-space mesh split into two page-local pieces** with the seam passing through one screenshot, then verify correct geometry and UV mapping on **both** pages simultaneously. The GPU stage must not be called successful before its actual guest checks pass. All public assets and test textures remain invented; the existing owner-held NPEB00148 source DDS must be privately validated before any game-content integration.
