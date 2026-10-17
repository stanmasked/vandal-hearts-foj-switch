# Flames of Judgment PS3 texture reconnaissance — evidence-first workflow

**Status (stage 145, October 17, 2026): no original FoJ PS3 texture
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

## Stage 142: candidate layout and possible container references

After the stage-141 scan, derive a **metadata-only** view of potential
linear image spans and candidate relationships:

```sh
python3 -m tools.foj_texture_relations \
  local-data/foj-texture-candidates.json \
  --output local-data/foj-texture-layout.json
```

This uses the existing private JSON report only: candidates are grouped
by relative source filename and ordered by file offset. It reports
hypothetical end offsets for **known-size** DDS payloads, and whether the
next header appears adjacent, separated, or overlapping. Unknown
FourCC/size headers stay explicitly unclassified. A negative gap may be a
false-positive magic signature or non-linear container format, *not proof*
that real texture payloads overlap.

Optionally perform a **strictly bounded, read-only heuristic check** for
32-bit file-relative offsets (both little- and big-endian):

```sh
python3 -m tools.foj_texture_relations \
  local-data/foj-texture-candidates.json \
  --root /path/to/private/foj-extracted \
  --pointer-prefix-bytes 65536 \
  --output local-data/foj-texture-relations.json
```

This second mode reads at most 64 KiB from the beginning of each
candidate-bearing file (configurable to at most 1 MiB). Only
4-byte-aligned words matching a candidate DDS **file offset** are noted.
Matches inside DDS candidate spans are ignored; no original bytes are
copied into output. The default record limit is 16 reference hints per
candidate, and directory traversal or symlink references in an untrusted
report are rejected. All output stays local and is covered by
`local-data/` in `.gitignore`.

**These are just pointer coincidences, never verified material/model
references.** They are particularly uncertain when formats use relative
offsets, segmented files, compressed indices or proprietary RSX layouts.
The tool cannot identify asset ownership, link textures to models or
claim a specific container type without independent real-file evidence.

## Stage 143: hypothetical fixed-stride offset tables

The stage-142 pointer report can be analyzed **without re-opening any source
asset files**, to discover short runs of potential DDS file offsets placed at
uniform 4-, 8-, 12-, 16-, 24- or 32-byte strides:

```sh
python3 -m tools.foj_resource_table_hypotheses \
  local-data/foj-texture-relations.json \
  --output local-data/foj-table-hypotheses.json
```

The command requires a stage-142 JSON report generated **with** `--root`
to include possible LE/BE pointer coincidences. It requires at least
three distinct DDS candidate targets per proposed run by default.
`--min-distinct 2` is available for broader exploratory scans, but will
produce substantially more false positives.

This analyzer works **only from existing numeric metadata**. It verifies
relative paths and numeric bounds, discards ambiguous interpretations at a
single pointer position, rejects unsupported endian labels, limits input
size and number of reported tables, and suppresses shorter patterns that
are subsets of a larger fixed-stride run. It reports possible tables with
their file name, starting word position, stride, endian, entry count and
candidate DDS offsets. It does not copy pixels, models, byte strings or
container contents.

**No table is proof of a texture-index, material slot or model link.**
Four sequential numerical matches can be a coincidence, debugging data
or arbitrary binary words. In particular, there is still no identified
FoJ asset container format. An actual material binding would require
independent structure evidence from privately inspected files, not just a
repeating pointer pattern.

## Stage 144: index-like fields and negative-control comparisons

Use stage-143 table hypotheses with the same private extracted directory
to **observe numerical index patterns in adjacent words**, without assuming
a material or model format:

```sh
python3 -m tools.foj_index_column_controls \
  local-data/foj-table-hypotheses.json \
  --root /path/to/private/foj-extracted \
  --output local-data/foj-index-observations.json
```

For hypothetical fixed-stride tables of **four or more rows**, the tool
examines other 32-bit words before or after the proposed pointer slot.
It labels exact ascending `0, 1, ..., N-1` sequences and dense
zero-based permutations, using the table's candidate byte order. It
does not treat repeated values or arbitrary increasing integers as
established indices. Runs with only one four-byte word per row or fewer
than four rows remain ineligible by default.

As a **negative control**, up to 256 windows sampled elsewhere in the
same file prefix are independently checked for similar dense
zero-based sequences. A hit outside the supposed pointer table adds the
observation `index-like-with-control-matches`; multiple candidate
fields are labeled ambiguous, and zero controls are never represented
as evidence of semantic correctness. These counts are descriptive, **not
a statistical confidence score** and not proof of causality.

The script reopens local files **read-only**, validates relative paths and
symlinks, and reads no more than 64 KiB from each file by default
(1 MiB maximum). It outputs relative filenames and strictly bounded
numeric pattern summaries, not model identifiers, pixel data, binary
records, shader data or commercial textures. All reports should stay
under gitignored `local-data/`.

**Even a clean index sequence does not identify a FoJ material index
or model table.** Verification requires independent evidence from
actual private FoJ resource files and ultimately correct on-console
rendering. Original FoJ package parts were not available to run these
heuristics on real game data during stage 144.

## Stage 145: cross-report consistency triage (not independent evidence)

After stages 142–144 have generated their **private local** JSON reports,
compare the metadata of all three stages without reopening any game data:

```sh
python3 -m tools.foj_evidence_triage \
  --relations local-data/foj-texture-relations.json \
  --tables local-data/foj-table-hypotheses.json \
  --indices local-data/foj-index-observations.json \
  --output local-data/foj-evidence-triage.json
```

The tool checks whether each proposed fixed-stride table entry actually
has a matching file-relative pointer hint in the stage-142 report, whether
its DDS candidate still exists, whether candidate payload spans conflict
with subsequent headers, and whether the matching stage-144 index-column
observation was missing, ambiguous, or had hits in the independent
control windows.

It assigns descriptive **internal triage** labels, not probabilities:

- `internally-contradicted`: missing target DDS, pointer hint not present
  in the earlier report, or overlapping known-size candidate spans
- `insufficient-or-ambiguous`: unknown texture size, missing/negative
  index observation, multiple possible index-like fields, or similar
  dense index patterns found in control windows
- `internally-consistent-for-private-review`: the metadata reports agree
  with no flagged contradiction or ambiguity; **still not independently
  validated and never evidence of a confirmed material/model link**

The new tool reads **only JSON**, checks report schemas and numeric
bounds, writes a metadata-only summary and keeps source files local.
The stage-144 negative-control scan is **sampled, not exhaustive**:
an absence of observed control matches must not be interpreted as a
confirmed absence of false positives. For local investigations, raising
its `--control-windows` limit can reveal additional coincidences.
Even when stage-142, -143 and -144 agree, their evidence is **not
independent**: all three come from the same candidate scans and
pointer coincidences. No "confidence score" or game-asset schema is
claimed, and no original FoJ game file has been inspected here.

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
