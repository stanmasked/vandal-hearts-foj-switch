# Real FoJ PSARC manifest: verified asset inventory

**Date:** 2026-10-16. All values below were obtained directly from the
user-provided European PS3 archive, using the public non-finalized PKG
SHA1-XOR stream format. **No commercial asset bytes are committed to GitHub.**

Parent PKG details and hash:
[REAL_PKG_NPEB00148.md](REAL_PKG_NPEB00148.md).

## Major breakthrough: actual game-data table

The PS3 debug/non-finalized package has 21 named items: five directories,
the game SFO/icon/logo, a PS3 SELF executable, a large PSARC resource archive,
nine Bink movies and a trophy archive. Details below:

| Content | Evidence | Compressed/package length |
| --- | --- | ---: |
| `USRDIR/cdata.psarc` | `PSAR` signature, zlib TOC | 235,982,224 bytes |
| `USRDIR/EBOOT.BIN` | `SCE\x00` executable container signature | 1,679,408 bytes |
| `PARAM.SFO` | PSF SFO, title `Vandal Hearts: Flames Of Judgment` | 1,040 bytes |
| `USRDIR/data/movies/*.bik` | nine `BIKi` Bink files | individual files vary |
| `TROPDIR/NPWR00877_00/TROPHY.TRP` | trophy bundle item | 1,232,976 bytes |

SFO metadata also confirms:

- `TITLE_ID`: `NPEB00148`
- `VERSION` / `APP_VER`: `01.00`
- `PS3_SYSTEM_VER`: `03.4000` (metadata minimum, **not** an emulator test)

The archive table gives names, nominal uncompressed item lengths, offsets
and type flags. The referenced executable has only been signature-tested;
it has **not** been converted to ARM64 code.

## PSARC container

| Field | Verified result |
| --- | --- |
| Magic | `PSAR` |
| Version | `0x00010004` |
| Block compression | `zlib` |
| TOC size | 117,022 bytes |
| TOC entry size | 30 bytes |
| TOC entries | 3,213 |
| First entry | UTF-8 filename manifest (114,689 bytes) |
| Manifest resource paths | **3,212** |
| Compression block size | 65,536 bytes |
| Archive flags | `0x01` |

The PSARC manifest was successfully decompressed from the two original
PKG fragments without extracting the game to disk.

### Manifest extension counts

| Extension | Count | Notes |
| --- | ---: | --- |
| `.tga` | 1,479 | Initial sampled files have `DDS ` signature, **not classic TGA** |
| `.bmodel` | 583 | Proprietary-looking 3D model container (not yet parsed) |
| `.banim` | 450 | Proprietary-looking animation data (not yet parsed) |
| No extension | 228 | Mixed content |
| `.txt` | 173 | Text and timing/metadata |
| `.ini` | 131 | Configuration and map settings |
| `.lua` | 51 | **Readable Lua scripts**, including named battle maps |
| `.coll` | 34 | Candidate collision/map data; sampled files are textual |
| `.vis` | 34 | Candidate visibility/map data; sampled files are textual |
| `.bfont` | 21 | Font-format resources |
| `.cgelf` | 21 | ELF-header compiled shader resources, not Switch-ready |
| `.bnd` | 5 | Bundle/resource list |
| `.png` | 1 | Image |
| `.xlsx` | 1 | OpenXML spreadsheet format |

**Total: 3,212**.

### Grounded map and scripting inventory

The manifest specifically includes:

- 113 entries in `data/maps/` — 45 `.ini`, 34 `.coll` and 34 `.vis`.
- 51 entries in `data/script/` — including battle map scripts such
  as `map1-1.lua`, `map2-7.lua`, `map3-10.lua`,
  and `map4-20.lua`, alongside shared scripts
  `combat.lua`, `Cinematic.lua`, `SaveVars.lua` and `WorldMap.lua`.
- 21 entries in `data/shaders/`.
- 229 entries in `data/config/`.

Some in-archive files have misleading extensions: the tested `.tga` assets
start with DDS magic and an expected 128-byte DDS-style header. The common
asset loader must use **file signatures**, not extensions, to select decoders.

No inference is made that all models, animations, or game rules are readable
yet; only the manifest and specific small previews were inspected.

## Repeatable code and tests

- `tools/inspect_debug_pkg_assets.py` — read-only random-access
  PKG + PSARC manifest scanner, using the local user-held split ZIP.
- `tests/test_inspect_debug_pkg_assets.py` — synthetic end-to-end tests
  verifying random reads, SHA1-XOR symmetry, file bounds, manifest decoding
  and error handling. No real game bytes are in CI.

Run from repository root:

```sh
python3 -m tools.inspect_debug_pkg_assets \
  "/path/to/Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.001" \
  "/path/to/Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg.zip.002" \
  --json > local-psarc-inventory.json
```


The command outputs **names, sizes and aggregate statistics only**.
It does not write or redistribute games, game scripts, executable data,
textures, audio, movies or licenses. Review any locally generated report
before sharing.

## Engineering implications

1. The dominant game archive can be **indexed** without an emulator, giving
   us a real map/resource inventory.
2. Build platform-neutral readers for the game-defined `.ini`, `.vis`,
   `.coll`, `.bmodel`, `.banim` and DDS-style resource formats.
3. Lua appears to be used for map/event scripts; verify APIs and data flow
   before implementing a Lua runtime or re-creating battle systems.
4. PS3 `EBOOT.BIN` is a SELF container; it cannot simply be turned
   into a Switch NRO. Compiled PS3 shader blobs also require a new backend.
5. Keep all proprietary bytes private/local. Eventually, an asset loader could
   read **user-provided local game data** on their own Switch; distributing
   the proprietary archive in the project's binary is out of scope.

This is a resource format *discovery* milestone, not a playable port.
