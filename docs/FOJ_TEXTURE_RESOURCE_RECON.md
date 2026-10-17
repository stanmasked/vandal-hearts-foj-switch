# Flames of Judgment PS3 texture reconnaissance — evidence-first workflow

**Status (stage 141, October 17, 2026): no original FoJ PS3 texture
container, swizzling scheme or texture-format distribution has been
confirmed by an actual resource dump.** The existing Switch renderer supports
a deliberately narrow classic DDS subset and small private texture atlases;
that support is **not evidence** that FoJ PS3 assets use those layouts.

The earlier multipart PS3 package archive is **not available inside the
current repository or the research CI environment**. Do not upload the game
package, proprietary files, personal keys, or extracted pixels to GitHub.

## Local, read-only metadata reconnaissance

After preparing a private extracted directory **locally** using authorized
tools, run from this repository:

```sh
python3 -m tools.foj_texture_probe /path/to/private/foj-extracted \
  --output local-data/foj-texture-candidates.json
```

The command scans regular files (including DDS signatures **embedded**
inside other binaries) in bounded 1-MiB chunks. It does not decode, write,
extract, decrypt, upload or copy a game asset. It emits only:

- Paths relative to the chosen private directory and file-relative offsets
- DDS header dimensions, claimed FourCC/pixel layout and mip count
- Computed **candidate** payload lengths for common linear DDS formats
- Whether the declared payload fills the remainder of the file, appears
  truncated, contains additional data or has an unclassified format

Default limits: 20,000 regular files, each up to 512 MiB, up to 128
header signatures per file. Larger files are skipped; adjust
`--max-file-mib` or `--max-files` if needed. Symlinks are not followed.
The scan is deterministic for a stable directory tree.

The JSON report is written **only to the user-selected local path**.
`local-data/` is gitignored, and the GitHub test workflow uses exclusively
invented synthetic fixtures. The report itself contains filenames; review
those locally before considering even a metadata-only excerpt for sharing.

## How to interpret results

A DDS header is merely a **candidate**, not proof that an original FoJ
resource uses that texture layout. An embedded offset may point to a texture
inside a container, a dummy header or incidental bytes. A value of
`ends-at-file-boundary` only reflects generic linear DDS size calculations.
It does not validate RSX-specific swizzling, tiling, channel endian ordering,
mipmap offsets or material references.

Before implementing a game-specific loader, corroborate any claimed format
using independent evidence: several user-owned files with consistent
headers, container indexes, known offsets and dimensions, and locally
inspected image output. Keep original files outside this repository.

## Existing native Switch capabilities and current limits

The research deko3d NRO can ingest **user-local** classic DDS images using
RGBA8, BGRA8, BC1/DXT1 and BC3/DXT5, with a validated complete mip chain.
It decodes only level 0 into RGBA8. Base atlas dimensions are limited to
256×256 and there are only two synthetic research material slots.
No actual FoJ scene rendering or direct import of PS3 graphics is proven.

Neither a passing metadata scan nor passing devkitA64 CI verifies image
presentation, texture sampling or correct material mapping on a physical
Switch. Continue to use `docs/GPU_SWITCH_SMOKE_TEST.md` for the independent
hardware smoke-test checklist.

## Follow-on experiments after actual local evidence

1. Compare header candidates from **real privately extracted** FoJ files
   against the formats supported by `gpu/atlas_dds.c`.
2. Classify unsupported sources without guessing; establish whether they
   are DDS, compressed archive members, PS3-specific containers or just
   arbitrary binary data.
3. Use non-proprietary generated fixtures to test any new layout converter;
   never add commercial source assets to GitHub.
4. Confirm GPU upload/presentation separately on the target hardware.
