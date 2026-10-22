# Stage311 — horizontal BC1 atlas page boundary research

**Base:** Stage310 [Draft PR #195](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/195). Both Stage310 GitHub GPU workflows successfully rendered eight different colors along a **vertical** 256-row seam. This research module studies the orthogonal seam direction without changing any existing Switch NRO.

## Problem

A 1024×1024 BC1 atlas decoded into 256×256 independent GPU pages has horizontal page boundaries as well as vertical boundaries. For atlas rows 511/512, the *last decoded row of page (1,1)* must interact with the *first decoded row of page (1,2)*. Reusing the Stage310 last-column logic would silently rotate the wrong texture coordinates. A horizontal seam needs a separately validated source-to-destination mapping.

## Native C reference

- `foj_stage311_horizontal_bilinear()`: for local X 0..255, samples the last texel row of upper page (1,1) and first texel row of lower page (1,2). It checks the existing **actual Stage303 1024 atlas UV resolver** against the original texel coordinates (256+x,511)/(256+x,512), and only accepts normalized atlas V from 511.5/1024 to 512.5/1024. At V=0.5 it gives the exact round-nearest blend on all four RGBA channels. Invalid V, X, pointer or buffer sizes preserve caller output.
- `foj_stage311_build_horizontal_gutter()`: builds one caller-owned 256×256 RGBA8 gutter, with rows 0..127 copied from the top page's decoded row 255, and rows 128..255 copied from bottom page's row 0 **for each individual X column**. It independently computes 256 bilinear midpoints, counts contrasting and actually intermediate samples, rejects any alias of gutter/report with either input, and only copies the completed temporary output after successful processing.

Unlike Stage309's invented foreground geometry, Stage311 does not draw a GPU pixel and does not claim hardware operation. This adds a 2D orientation contract needed before an actual horizontal seam NRO can be trusted.

## Native end-to-end tests and restrictions

A synthetic canonical 1024² DDS contains eight different 32-pixel-wide vertical color bands across each of pages (1,1) and (1,2). It is actually decoded by Stage301 `foj_bc1_1024_decode_page()`; the test inspects **all 256 columns × all 256 gutter rows**, validates source-copy immutability, correct horizontal bilinear midpoint and both texel-center endpoints. Tests also verify failed calls for null pointers, NaN/inf, V/X bounds, short and oversized buffers, and output/report overlapping either source buffer. Two matching page inputs must report 0 contradictory mixes.

GitHub Actions run GCC and Clang optimized native C, GCC UBSan, and Clang ASan/UBSan; no game assets, private DDS/ROM contents or original PS3 paths are written to public artifacts.

## Next work

Implement a distinct horizontal foreground seam quad in an opt-in deko3d research NRO, then require two actual NeXium frames showing all eight column-varying color pairs and their mixed colors at the horizontal midline. Real game UV topology, arbitrary polygon crossings and physical Nintendo Switch parity are not claimed.
