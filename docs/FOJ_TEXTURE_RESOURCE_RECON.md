# Flames of Judgment PS3 texture reconnaissance — evidence-first workflow

**Status (stage 148, October 17, 2026): no original FoJ PS3 texture
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

## Stage 146: reproducibility check across two separate private cohorts

After processing two **separately acquired or independently sampled local
directories** through the preceding stages, compare the stage-145 reports:

```sh
python3 -m tools.foj_holdout_replication \
  --baseline local-data/baseline/foj-evidence-triage.json \
  --holdout local-data/holdout/foj-evidence-triage.json \
  --baseline-root /private/foj-cohort-a \
  --holdout-root /private/foj-cohort-b \
  --output local-data/foj-holdout-comparison.json
```

The tool compares **structural shapes only** (32-bit pointer-table stride
and byte order) among stage-145 internally consistent entries. It ignores
absolute offsets and table row counts so that the same hypothesized
record layout can occur in different-sized containers. It records
whether the pattern was repeated, absent, ambiguous or contradicted in
the second cohort. Use `--min-consistent 2` to require two
non-contradictory tables in each cohort before labelling a repeated
pattern.

To reduce accidental data reuse, the two roots must exist, must not be
the same or nested, and neither may be a symlink. Every referenced file
must be a regular file with no symlink path component. Shared hardlink
inodes across cohorts are rejected, even under different filenames.

**This does not prove genuinely independent evidence.** Separate files
may contain duplicate or copied content, and these JSON reports cannot
prove original game provenance, verify an RSX format or identify an actual
FoJ material/model link. The tool does not hash or expose private file
contents; the output contains aggregate pattern counts only, with no
absolute paths or raw source bytes.

The labels `repeated-unverified-pattern`,
`not-reproduced-in-holdout`, `holdout-contradiction-observed`,
`holdout-ambiguous` and `holdout-only-unverified-pattern` are
**descriptive**, not confidence scores or claims that a gameplay
renderer can import the PS3 assets.

Use **different privately owned original-resource subsets** when
available, rather than copied synthetic fixtures. No original
Flames of Judgment PS3 resource dump was available at implementation.

## Stage 147: deterministic synthetic stability and false-positive matrix

Run a self-contained regression stress test with **invented** DDS buffers
and two temporary local synthetic cohorts:

```sh
python3 -m tools.foj_stability_matrix \
  --output local-data/foj-synthetic-stability.json
```

The tool runs the entire existing metadata pipeline in memory and temporary
directories: DDS header probe → candidate spans → possible pointer tables →
adjacent index/control checks → reason-coded triage → holdout comparison.

Seven fixed scenarios perturb table sizes (3–8 records), strides
(8 vs 16 bytes), little-/big-endian offsets, index permutations, repeated
numeric fields and a separate false-positive control window. It compares
**observed heuristic labels** to explicitly authored regression expectations.
If a label changes unexpectedly, the CLI writes a metadata-only report and
returns a nonzero exit code, suitable for GitHub Actions.

This is a **test of the tools, not a test of the original game**.
An expected label such as `repeated-unverified-pattern` means that
synthetic test data produced a predictable observation. The program does
not inspect a FoJ disc, decrypt PS3 content, validate asset provenance or
establish any original model/material mapping. Its JSON contains only
synthetic scenario descriptions and aggregate observations; generated
binary fixtures are discarded automatically.

This test also documents a deliberate detection boundary: a three-entry
table can be recognized as a numeric pointer-table candidate while
stage-144 index analysis (minimum four entries) marks the evidence
insufficient. Changes in heuristic thresholds may reasonably require
revising these authored expectations with new tests and justification.

## Stage 148: incomplete DDS payloads and container-corruption regression

Run the deterministic **synthetic-only** malformed-container matrix:

```sh
python3 -m tools.foj_corrupt_container_matrix \
  --output local-data/foj-corruption-matrix.json
```

This generates disposable fake DDS containers, then exercises the real
DDS inventory → candidate relations → table discovery → index checks →
reason-coded evidence triage pipeline. Twelve mutations cover corrupted
DDS magic/header size/width, multiple missing headers, a broken pointer
word, unaligned pointer placement, a partially available last DDS header,
a **complete DDS header with a truncated pixel payload**, an unsupported
FourCC, a genuinely unaligned *embedded DDS header*, and extra unrelated
container bytes. Unexpected classifications are reported and make the
command fail. No PS3 proprietary game files are needed or included.

The stage-142 report now carries an optional `payload_check` from the
stage-141 inventory. A `truncated` candidate must be marked
`dds-payload-truncated` and treated as `internally-contradicted` in
stage-145 triage, even if an aligned pointer table still points to its
header. This is only an **end-of-file bounds indication**; embedded DDS
containers can have external headers/footers, and a valid-looking stream
does not prove FoJ asset format. Existing reports without this optional
field remain readable.

A **DDS signature at an unaligned embedded byte offset is not
automatically corrupt**. Conversely, a pointer at an unaligned word
position is not discovered by the existing 4-byte-aligned pointer scan.
These distinctions are intentional: don't introduce false negative
claims about unknown PS3 container layouts.

Generated fixtures and temporary roots are deleted on exit. The JSON
report contains scenario names and aggregate counts only. As with
all prior stages, these tests cannot establish an actual FoJ texture,
material/model link, and they do not test Nintendo Switch GPU rendering.

## Stage 149: deterministic four-report replay gate

Before interpreting an existing local stage-145 triage report or comparing
cohorts, independently **replay the saved JSON chain**:

```sh
python3 -m tools.foj_report_replay_audit \
  --relations local-data/foj-texture-relations.json \
  --tables local-data/foj-table-hypotheses.json \
  --indices local-data/foj-index-observations.json \
  --triage local-data/foj-evidence-triage.json \
  --output local-data/foj-report-replay.json
```

The stage-149 command performs these checks **without opening original
PS3 files**:

- Re-derives all stage-143 hypothetical tables from stage-142 JSON with
  the saved minimum-distinct-target setting and compares the *complete*
  derived result, including summaries, against the saved stage-143 report.
- Requires exactly one stage-144 observation for each table, rejecting
  missing/duplicated rows, unsupported prefix bounds, impossible field
  deltas, inconsistent index labels or control-window counts.
- Re-runs stage-145 triage and checks the entire saved outcome, including
  its reason codes and aggregate counts; changed/stale triage is rejected.
- Uses bounded input files, refuses symlink report paths and duplicate
  JSON object members, and emits **aggregate-only** replay counts rather
  than filenames, raw bytes or private report content.

A replay **passes even for internally contradicted DDS hypotheses**, provided
the saved contradiction can be reproduced. It is not a quality score.

**Important limitation:** deterministic agreement is not provenance.
Someone can consistently edit all four JSON reports; the underlying private
files may also change between the stage-141 scan and stage-144 prefix read.
The command does not independently validate original PS3 resource identity,
material bindings, container semantics, successful DDS decoding, or Switch
hardware output. Store local reports together and never upload proprietary
game resources. Any failure requires regenerating and rechecking reports
from the user's local source data instead of silently accepting mixed runs.

Python 3.10/3.12 CI executes generated-only replay, corruption, malformed
metadata, stale-report and CLI privacy tests. This is an offline research
integrity gate, not progress on the playable game's engine.

## Stage 150: source-tree coherence across analysis stages

The earlier report-replay gate checks saved JSON, but cannot detect a game
resource changed between stage-141 header scanning and stage-144
index/control scanning. Run the existing pipeline under two read-only,
in-memory SHA-256 source snapshots, with a NEW output directory:

    python3 -m tools.foj_source_coherence_gate \
      /path/to/private/foj-extracted \
      --output-dir local-data/foj-coherent-run-001

The tool performs source snapshot A, then stages 141 (DDS inventory), 142
(relations/pointer read), 143 (hypothetical tables), 144 (index/controls),
145 (consistency triage), followed by source snapshot B and stage-149 JSON
replay. Both snapshots record file and directory names, file identity,
permissions, size, change/modify timestamps and SHA-256 content IN MEMORY.
A missing/new file, in-place modification, changed inode, unsupported
entry or symlink causes a hard failure. The DDS inventory must cover
every regular file in the selected source tree; skipped or unreadable
files are rejected rather than silently claimed coherent.

Defaults are 20,000 files, 512 MiB per file and 1,024 MiB total per
snapshot. For a larger source tree use --total-mib, up to 65,536 MiB.
Unlike stage-141 reconnaissance, this strict gate refuses oversized,
symlinked and non-regular entries instead of skipping them.

Only after success, seven metadata-only JSON files are written into a
fresh directory outside the source tree. Some reports contain private
source-relative filenames. Keep them under gitignored local-data/ and
never publish them. The final foj-source-coherence.json records only
aggregate counts/statuses, never file paths or hashes. A failed scan
does not create the new output directory.

**Scope and limits:** two matching snapshots catch ordinary changes
during processing but cannot prevent a malicious writer from swapping
source bytes between reads, restoring contents and spoofing metadata.
The stage-141 and stage-144 readers are not fd-bound to the snapshots.
Neither source provenance, game-specific PS3 container semantics nor
Nintendo Switch rendering is proven. Deterministic metadata replay is
not evidence of a playable port.

Python 3.10/3.12 CI uses disposable invented DDS buffers only, testing
in-place byte changes, timestamp changes, added/deleted files,
symlinks, resource limits and fail-closed publication. No original PS3
resources or fingerprints are included in the repository.

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
