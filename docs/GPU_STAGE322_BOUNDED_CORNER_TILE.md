# Stage322 — bounded four-page RGBA8 corner tile from original BC1 page texels

## Provenance

Stage316 successfully rendered a synthetic four-page junction in the
NeXium deko3d research GPU using a preassembled RGBA corner material.
Stage317 resolved bilinear texels across sixteen decoded BC1 atlas pages.
Stages318–320 mapped synthetic UV triangles to geometric/filter-source
pages and deterministic CPU batches. Stage321 planned three physical
GPU texture slots and deferred any batch requiring four or more source
pages with PATCH_REQUIRED, without an invented draw call.

Stage322 resolves one precise, bounded subset of those deferred cases:
**a four-page 2×2 junction** at any of the nine internal corners of the
4×4 atlas. Four other arrangements (for example a long horizontal strip)
or larger page sets are deliberately unsupported.

## Tile semantics and size

A junction at source atlas texel coordinate (x = 256*page_x,
y = 256*page_y), with page_x and page_y each in [1,3], uses four
independently decoded 256×256 RGBA8 pages (NW, NE, SW, SE).

Stage322 copies exact source texels into a **16×16×4 byte (1 KiB)**
contiguous RGBA8 tile with atlas origin (x-8,y-8):

- tile upper left 8×8: NW source columns/rows 248..255
- tile upper right 8×8: NE source cols 0..7, rows 248..255
- tile bottom left 8×8: SW source cols 248..255, rows 0..7
- tile bottom right 8×8: SE source cols/rows 0..7

This is a faithful pixel splice, not a fabricated 4-color gradient or
four averaged blocks. Future bilinear GPU sampling of this **single**
bounded tile would see exactly the four source texels surrounding the
seam; its UV transform must be handled by a separate verified renderer.

The receipt includes atlas texel origin, the exact four-page source mask
and individual ids, bilinear midpoint RGBA, byte count, and FNV-1a 64-bit
hash of precisely 1024 output bytes.

## Strict fail-closed conditions

Accept only a genuine Stage321 PATCH_REQUIRED command whose filter mask
equals exactly the relevant 2×2 four-page combination, whose geometry
mask is a nonempty subset and halo mask matches. Reject any pre-existing
bound or uploaded slot on a deferred command, invalid/duplicate residents,
wrong junction, wrong page lengths, null pointers, overlapping source pages
or output/report/source/cmd memory, and any wrong output size.

The output tile and receipt are entirely unchanged upon rejection, and
source pages are never modified. Construction uses a bounded 1 KiB
local staging buffer before a single commit. No heap or file I/O.

## Native generated-only tests

For each of the **nine** internal atlas corners:

1. Build a synthetic NW triangle just inside the junction, derive its
   four-page bilinear mask through Stage319, batch with Stage320, and
   obtain a genuinely deferred command from Stage321.
2. Build the 1 KiB tile from four unique source pages with coordinate-
   dependent RGBA values (including alpha).
3. Independently check all 256 tile pixel values against their original
   page/local pixel, all four page ids, atlas origin, exact FNV checksum.
4. Independently compare **25 subpixel positions** across the seam to
   Stage317 original 16-page bilinear sampler (225 total references).
5. Rebuild the same tile to confirm exact output repeatability.

Negative cases exercise malformed command/filter/halo/slot metadata,
wrong page junction, source aliases, wrong source and output lengths,
nulls, output/report overlap, and unchanged outputs and input page hashes.

Four GitHub Actions configurations: GCC, Clang, GCC UBSan,
Clang ASan+UBSan. Every byte used in public CI is invented test data.

## Boundaries of this result

This is a native CPU **tile construction** and verification milestone.
It does NOT bind the tile to deko3d, upload GPU memory, rewrite UVs,
split original triangles, prove a new NeXium GPU screenshot, verify
transparency draw order, import original FoJ resources, or test physical
Switch hardware.

The Stage321 PATCH_REQUIRED command is still not a drawable command
until a later renderer explicitly validates and binds this tile.

The user's original NPEB00148 PS3 game package, other original resources,
and any raw guest logs remain private. This remains a stacked Draft PR
and does not modify main.
