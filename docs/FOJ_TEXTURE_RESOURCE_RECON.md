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

## Stage 151: descriptor-bound DDS reads and path-swap regressions

Stages 141, 142 and 144 no longer read game data through an
"inspect pathname, then reopen pathname" sequence. The shared
`tools/foj_fd_bound_reader.py` helper instead opens the root
directory and each intermediate directory with descriptor-relative
`os.open(..., dir_fd=..., O_NOFOLLOW | O_DIRECTORY)`, then
opens the final regular file with `O_NOFOLLOW | O_NONBLOCK`.

The opened file descriptor is checked using `fstat` for file
type, inode, device, size and modification/change timestamps. The same
metadata is checked again after the caller finishes reading it. Stage 141
also compares the descriptor identity with its pre-open `lstat`
and aborts when a file was substituted. Stages 142 and 144 use the same
fd-bound prefix reader, so symlink replacement at open time cannot redirect
those tools outside the requested local input root.

The scanner still finds embedded DDS headers in 1 MiB chunks and
preserves the existing metadata schema; no texture pixels are copied into
the reports. The stage-150 complete-tree SHA-256 pre/post snapshots,
stage-149 deterministic JSON replay, and metadata-only output requirements
remain unchanged.

The synthetic stage-151 tests cover valid nested files, traversal
rejection, symlinked roots/parents/files, directory/FIFO rejection,
same-inode edits during reads, file/parent-directory substitution
**at the exact open call**, and full DDS candidate-to-index pipeline
compatibility. They contain no original PS3 files.

**Security boundary:** fd anchoring prevents symlink path redirection
at actual source opens, but it does not provide a cryptographically
immutable byte stream: another process can modify the already opened
regular file while it is being read, or restore contents between
snapshots. The stage-141 pathname discovery still uses `os.walk`
and is not a fully descriptor-relative directory enumeration. Stage 150
remains necessary for detecting ordinary tree changes and incomplete
inventory. Neither tool establishes source authenticity, actual FoJ
resource semantics or Nintendo Switch rendering.

## Stage 152: descriptor-relative DDS directory enumeration

The stage-141 DDS candidate inventory now enumerates its input directories
using anchored directory file descriptors and `os.scandir(directory_fd)`,
rather than `os.walk` and subsequent path reopening. The
root is opened with `O_DIRECTORY | O_NOFOLLOW`; every child
directory is opened relative to the parent descriptor under the same
no-follow contract. Files are opened with the stage-152
`open_regular_at(parent_fd, name)` routine. Directory
and file identity, type, size and timestamps are compared before opening,
after reading and, where appropriate, after exiting the child directory.

Sorted filenames are processed before sorted subdirectories, retaining the
previous inventory order and JSON schema. Known symlinks and special files
are counted as skipped rather than followed, including symlink directories.
The stricter stage-150 coherence gate rejects any skipped entries. File and
directory count bounds, a 128-level directory depth bound, bounded DDS
header scanning and existing `max_file_bytes` behavior remain.

Deterministic generated-only tests inject symlink and regular-file
substitutions **at the child directory open operation**, inode replacements
after file reads and directory changes during scanning. A separate test
checks that the stage-150 gate does not silently accept symlink skips.

**Limits:** this is a read-only directory enumeration improvement, not a
filesystem snapshot or a proof of immutability. Concurrent writers may
still modify an opened file between reads, or change entries and restore
them before comparison. The user-selected root's ancestor components
are not all individually anchored, and only Linux/POSIX-style systems
providing the necessary `dir_fd` and `O_NOFOLLOW`
capabilities are supported. The tool does not verify FoJ asset provenance
or execute original PS3 gameplay or a Nintendo Switch GPU frame.

## Stage 153: bounded directory membership and stable readdir observations

Stage-152 fd-relative enumeration previously built and sorted a complete
unbounded list of names in each directory, even when the DDS file-count
limit was low. Stage 153 now uses a shared, read-only
`bounded_directory_names(dir_fd, ...)` routine. Both stage-141
DDS inventory and both stage-150 SHA-256 source-tree snapshots enforce
limits **as names are received**, before sorting/allocating more entries.

Defaults: **20,000 entries per directory**, and **4 MiB of encoded
filenames per directory**; absolute configurable ceilings are 100,000
entries and 64 MiB. All entries count, including symlinks, special
files and subdirectories, not just scanned DDS-containing files. Use
`--max-dir-entries` and `--max-dir-name-bytes` on
`python -m tools.foj_texture_probe` or
`python -m tools.foj_source_coherence_gate` to override
within the hard bounds. A limit breach raises a generic error without
revealing source names; neither a truncated list nor a partial pipeline
may be accepted as a complete evidence report.

The inventory and source snapshots now enumerate each directory again
after processing it and reject different sets of names; existing fd
identity, timestamp and SHA-256 comparisons remain in place. Repeated
enumeration is an **integrity check, not an atomic filesystem snapshot**.
An attacker can still change and restore entries between observations.
The same filename appearing twice in one enumeration is rejected.

New standard-library regressions use temporary invented directory floods,
synthetic extremely long scandir streams, duplicate names, byte-budget
violations, symlink floods and deliberate first-vs-second-list changes.
A stable nested DDS fixture must still pass the complete metadata/replay
pipeline. Tests neither process original PS3 data nor prove FoJ
container semantics or Nintendo Switch GPU operation.

## Stage 154: full byte replay within anchored DDS file reads

Stage 153 checked inode/size/timestamps and directory membership, but a
same-sized write could change bytes during DDS scanning. Stage 154
adds SHA-256 content replay to stage-141 DDS inventory and its direct
candidate-header iterator. The first digest is accumulated from the bytes
**actually read by the parser**; after header scanning (even when the
bounded `max_hits_per_file` count is reached early), the
rest of the source file is read to EOF and hashed. The same already-open
regular file descriptor is then rewound and **the complete file is read
again**. Both length and SHA-256 must match before candidate metadata
can be accepted. Header candidates are held only in bounded memory
(up to 4096 headers), so no half-verified candidate is yielded by the
direct iterator.

Stages 142/144 now immediately read their small file prefix twice
through the same anchored descriptor and reject mismatched bytes. The
stage-150 two full SHA snapshots remain an independent cross-stage
coherence requirement. The reports retain the existing JSON schemas;
neither raw payloads nor SHA-256 fingerprints are written to the
metadata reports. The cost is an extra whole-file read for each scanned
regular file and an extra prefix read for pointer/index analysis.

Generated-only regression tests inject same-size changes immediately
before hash replay, after the first DDS header and in an unscanned tail
after the header cap. They also test empty/no-DDS files, truncation,
file growth, direct iterators, prefix replay and failure to publish
incomplete stage-150 reports.

**Security limit:** two sequential reads are not an atomic snapshot,
cannot prove original game provenance, and cannot defeat an adversarial
writer who makes and restores changes between observations. File
timestamps and inode checks remain necessary. The actual private
Flames of Judgment container format, game renderer and Nintendo Switch
hardware execution are not verified by these synthetic tests.

## Stage 155: global DDS candidate and JSON metadata budgets

The stage-154 scanner already restricted each file to at most 4,096
header hits, but thousands of separate files could still accumulate an
unbounded total number of candidate dicts. Stage 155 adds two **global,
fail-closed** limits for the stage-141 inventory:

- At most **8,192 validated DDS header candidates** per inventory by
  default (configurable maximum: 65,536).
- At most **8 MiB of candidate JSON metadata** by default (hard maximum:
  64 MiB), conservatively charged when each candidate is appended. This
  includes UTF-8 filename lengths and per-record pretty-print overhead.
  An exact full-manifest JSON-size check is also performed before return.

Use `--max-candidates N` and `--max-metadata-mib N`
on both `python3 -m tools.foj_texture_probe` and
`python3 -m tools.foj_source_coherence_gate`. The Python
API accepts a byte-exact `max_metadata_bytes` argument
(useful for tests). Unlike the separate source-file count limit, these
are total **metadata** restrictions and cannot be bypassed by splitting
DDS candidates across files or nested directories.

When either limit is exceeded the tool raises a generic error rather
than publishing a truncated report marked as complete. The stage-150
publication process stops before creating its new output directory.
The old JSON report schema is unchanged, and no raw asset bytes or
fingerprints are exported by these budgets. All earlier read-only,
descriptor-bound, two-pass SHA-256, and privacy checks remain intact.

The generated-only test matrix covers multi-file DDS floods,
UTF-8 metadata-size accounting, exact count boundaries, invalid
bool/negative/excessive limits, zero-candidate files, both command-line
paths, and no-partial-publication guarantees. Synthetic success says
nothing about the original game's resource layout or playable Switch
runtime. The estimated budget is deliberately conservative; a report
below the hard emitted JSON limit can still be rejected earlier due to
reserved bookkeeping overhead.

## Stage 156: bounded metadata transit through research stages

Previously stage 155 restricted candidate generation, but a user-supplied
stage-141 JSON file or a stage-142 layout expansion could still be passed
to later tools without the same byte budget. Stage 156 adds
`tools/foj_report_transit_budget.py` for stage-to-stage
JSON transfer. It measures **actual UTF-8 bytes of the canonical,
indented JSON** using an incremental encoder, limiting **each source
and generated report to 64 MiB** before downstream processing or
publication. Reports exceeding the bound fail closed: no partial
private report is intentionally written.

Independent stage 142 (layouts), 143 (table hypotheses), 144 (numeric
index observations), 145 (consistency triage), and 149 (deterministic
replay) now validate report objects on entry and return. Their CLI
readers open private input JSON via a no-follow regular file descriptor,
check file size **before reading**, verify metadata/size after reading,
reject duplicate JSON object members and malformed/non-finite JSON.
This replaces unbounded path-based JSON input reads in stages 142–145
and the larger former 149 reader allowance. The stage-150 complete
pipeline additionally limits its seven report outputs to **128 MiB in
total**; `--bundle-mib` permits a smaller configured
aggregate bound. All original report schemas are preserved.

This limits serialization and file-backed JSON input size, but does not
give a hard process RSS bound: Python object representation and
downstream table-search complexity can exceed serialized JSON size.
Standalone output path publication has not been made atomic by this
stage. Untrusted local files can still be concurrently changed; the
no-follow input check and timestamps are not a full filesystem
snapshot. No original PS3 resources or source hashes enter public
reports, and a passing test does not prove a game texture mapping or
Nintendo Switch GPU presentation.

Synthetic regression tests cover per-stage input/output checks,
Unicode byte counting, sparse oversized inputs, symlinks, duplicate
object members, malformed bytes, oversized CLI inputs, legitimate
multi-stage reports, and fail-closed stage-150 publication.

## Stage 157: indexed DDS span and table search

Stage 142 now merges overlapping DDS candidate byte ranges and scans
ascending aligned prefix positions using a monotone interval cursor.
This eliminates repeated per-word scans of every DDS interval. Relative
paths, pointer classifications and the output JSON schema are unchanged.
Reports with more than 65,536 candidate entries fail closed.

Stage 143 keeps the previous maximal-stride search and suppresses
subsumed candidate runs using binary searches over sorted arithmetic
intervals indexed by stride and remainder. Input points per endianness
are limited to 131,072; more than 32,768 provisional table runs are
rejected rather than emitted as an incomplete report.

Generated-only tests compare the optimized algorithms against the
stage-156 reference on deterministic randomized cases and exercise
2,500 disjoint hypothetical table runs. These are algorithmic checks,
not a measured general-purpose speedup guarantee. Source provenance,
actual FoJ resource formats and Nintendo Switch playback remain
unverified.

## Stage 158: reproducible, generated-only performance diagnostics

The standalone `python -m tools.foj_stage158_benchmark` command measures
two stage-157 metadata processing workloads: scanning DDS candidate spans
against a generated pointer prefix (stage 142), and discovering disjoint
three-entry hypothetical table runs (stage 143). These experiments do
**not** use commercial PS3 files, unpack user assets, or claim any
verified FoJ material/model associations.

The harness generates a fresh synthetic file and manifest inside a
temporary directory for each fixed-size case. Stable offsets, invented
DDS headers and invented pointer words ensure reproducible *inputs*.
Temporary source file paths and bytes are never included in the output.

There are three workloads/profiles:

| Profile | DDS candidates / table groups per case | Use |
| --- | --- | --- |
| `smoke` | 32, 128 | Short CI diagnostic |
| `standard` | 128, 512 | More representative local sweep |
| `stress` | 512, 2048 | Bounded upper-end local probe |

Sample command: `python -m tools.foj_stage158_benchmark --profile standard --repeats 3 --output local-stage158.json`.
The output file must not already exist. Each record contains the
case size, exact observed record count, **median elapsed milliseconds**
and **maximum tracemalloc-traced peak KiB**. The latter measures only
traced Python allocations, not total RSS, native allocator use, GPU
memory or Nintendo Switch hardware. Elapsed times vary by Python,
host load, filesystem and runner, even with identical inputs.

CI on Python 3.10 and 3.12 executes the small profile and verifies
that counts and source-private output rules are preserved. CI deliberately
does not require a particular elapsed time or benchmark speedup.
Benchmark reports are not treated as evidence of real FoJ decoding or
runtime performance and are not uploaded automatically.

## Stage 159: allowlisted CPU hotspot profiling

Run `python -m tools.foj_stage159_profile --profile smoke --repeats 2`
for deterministic synthetic-only cProfile measurements on stage-142
candidate-to-prefix relations and **full stage-143 hypothetical-table
inference**, including input validation and JSON budget checks.

The stage-158 fixture sizes (32/128, 128/512, 512/2048) are reused by
`--profile smoke|standard|stress`. The generated tables contain
three pointer observations per hypothetical table, so no commercial PS3
resource data or inferred game-specific material links are involved.

Stage 159 records median wall time and profiled total CPU time, plus a
small, fixed allowlist of function-phase labels: range indexing, prefix
reads, report byte validation, reference validation, and table-run
discovery. Calls and self/cumulative times are summarized by phase.
Use `--top-phases 1..8` to limit display and `--output` to
write a **new** metadata-only JSON file. Output never contains the raw
profiler call graph, source file paths, line numbers, input bytes,
temporary directory names, or private filenames.

**Interpretation:** a cumulative function time includes time spent in
nested functions, so cumulative phase times must not be added together.
Python's cProfile overhead also changes runtime relative to the
unprofiled stage-158 timings; both depend on host load and Python
version. These diagnostics are not pass/fail speed thresholds or proof
of memory efficiency. CI runs only the small, generated-only profile
and verifies semantic completeness and privacy filtering.

No actual FoJ container/material/model mapping or Nintendo Switch
rendering has been established by profiling.

## Stage 160: exact byte accounting without ASCII re-encoding

After synthetic stage-159 CPU profiling identified per-report JSON
measurement as a material expense, `measure_report()` now
checks each emitted JSON fragment with Python's `str.isascii()`.
For ASCII fragments the character length already equals the UTF-8 byte
length; this avoids allocating a temporary `bytes` object for each
piece of punctuation, indentation, JSON field name, or numeric text.
Non-ASCII fragments continue to use exact UTF-8 encoding and length
checking. The final trailing newline remains part of the budget.

This is a **safe fast path, not a new estimator**: reports are still
encoded incrementally and checked against the existing 64-MiB ceiling,
without constructing an entire second serialized copy. The first
over-budget fragment still aborts the pipeline. Surrogate-containing
strings that cannot be represented in UTF-8 are explicitly rejected
with a generic, private-data-free error.

The new synthetic test matrix verifies the optimized counter against
`json.dumps(..., indent=2, sort_keys=True, ensure_ascii=False)`
plus newline, including multilingual names, emoji, combining characters,
JSON escapes, random mixed strings, exact inclusive byte boundaries,
stage-142/143 and full stage-150 outputs. It also checks that ASCII
fragments are never re-encoded, Unicode fragments are byte-measured,
and malformed inputs fail closed. Stage-159 generated-only profiling
still runs in CI for follow-up measurements; the change is **not**
subject to machine-dependent timing gates or a guaranteed speedup.

These are metadata-processing improvements only. They establish
nothing about real Flames of Judgment textures, PS3 resource formats,
or execution on a Nintendo Switch.

## Stage 161: local DDS preflight for two Switch research materials

Run `python3 -m tools.foj_gpu_local_dds_preflight /private/dds-slots --output /private/gpu-intake-report.json` to inspect **user-selected, already-extracted or converted classic DDS** files, not PS3 packages or unverified FoJ resource containers.

The input directory has fixed optional names `material0.dds` and `material1.dds`. Missing slots report `synthetic-fallback` (matching the existing NRO). A present file outside the native GPU DDS contract aborts the entire report. Accepted formats match `gpu/atlas_dds.c`: classic RGBA8/BGRA8, BC1/DXT1 and BC3/DXT5, width 8–256 divisible by eight, height 1–256 (multiple of four for BCn), up to nine valid mip levels with a complete exact-length chain. The native decoder uploads **base mip level zero only**. DX10, arrays, cubemaps, PS3 tiling/swizzling, trailing bytes and missing mip bytes are not supported.

The tool reads bounded bytes twice from a pinned no-follow descriptor and checks inode/metadata before and after reading, though a malicious concurrent writer is not fully excluded. It emits only slot indices, dimensions, generic formats, mip counts and compatibility results. No private path, source filename, image data or hash appears in the JSON report. The output must be a new file. The native C atlas decoder itself supplies the acceptance oracle in synthetic host tests; native devkitA64/UAM build checks also run.

After separately verifying user-owned files, copy them **manually** to `sdmc:/switch/foj/gpu/material0.dds` or `sdmc:/switch/foj/gpu/material1.dds` on the Switch SD card. Do not commit game data, private DDS sources or local reports. A preflight success proves only structural support by the experimental decoder, not the provenance of FoJ textures or on-console image presentation.

## Stage 162: native DDS verified replay and synthetic Switch smoke

The experimental native C DDS loader in `gpu/atlas_dds.c` now reads every
bounded local DDS file twice on the SAME open stream, rejects changed bytes
and unexpected growth/truncation, and closes the file before decoding into
caller memory. No pixels or metadata are changed on a failed read. This is
a best-effort stability check, not atomic source capture: unlike stage-161
Python preflight, native `fopen()` still follows filesystem symlinks.

The command `python3 -m tools.foj_stage162_synthetic_dds ./stage162-smoke-dds`
creates a NEW directory containing two different invented 8x8 classic RGBA8
DDS checkerboards for native Switch GPU tests. A directory that exists
already is never overwritten. Run stage-161 preflight on those synthetic
files before copying manually to SD. Use the step-by-step hardware test
matrix at `docs/GPU_STAGE162_SD_SMOKE.md`, with both checkerboards, one
fallback, no files, invalid file and recovery. None of these changes
confirms PS3 texture or material provenance, or real on-console rendering.

## Stage 163: native DDS path checks and generic two-slot diagnostics

The native research DDS loader now uses a descriptor-backed `open` /
`fdopen` path with `lstat` and `fstat` identity checks. It rejects
final-component symlinks, directory entries, FIFOs and unexpected
replacement or metadata changes, in addition to stage-162 byte replay.
It uses `O_NOFOLLOW` when the target platform defines it; the
presence or absence of that flag does not make ancestor directories
unconditionally safe. The loader still operates on trusted, fixed SD
paths; this does not constitute a secure snapshot against hostile
concurrent rewriting or mounting semantics on Switch.

The compatible old 1/0/-1 function remains available. A new
`foj_atlas_dds_try_read_status` API distinguishes absent optional
slots, rejected path, failed I/O, changed data, unsupported DDS and
successful CPU decode. The experimental GPU NRO logs only material
slot numbers and generic outcome strings, not private paths, hashes,
pixels or game assets. Whether stderr can actually be seen on Switch
depends on its homebrew environment and is unverified. SDK-free C11,
NDEBUG and sanitizer test suites include symlink/FIFO/directory input
regressions; successful CI is not a hardware validation.

## Stage 164: GPU DDS intake screens

The existing shader-backed deko3d research NRO now displays two short
GPU-rendered solid-color screens before normal material draws: first
material 0, then material 1, 120 presented frames each. Colors encode
stage-163 generic DDS intake statuses, with no text, private path or
source bytes rendered. A malformed DDS produces a persistent failure
screen and a nonzero return code rather than an unexplained black frame
or incorrect silent fallback. The shader-free clear NRO is unaffected.
Pure C status/timing tests, host compiler tests and native devkitA64/UAM
builds check the implementation, but actual on-console image output
remains unverified. Consult `docs/GPU_STAGE162_SD_SMOKE.md` for the
complete color legend, interpretation and real-hardware observation plan.

## Stage 165: frame-command simulation and manual Switch smoke bundle

A platform-neutral C command planner now decides whether the GPU
presents a status color or a normal textured scene, keyed by
frame number, actually acquired swapchain buffer, number of observed
DDS slots and validated status array. An invalid state never produces
a command. Generated-only host tests simulate 4096 presented frames
for healthy, failed-first-slot, and failed-second-slot scenarios.
The native deko3d triangle research NRO calls this same planner.

A reproducible script `tools/foj_stage165_sd_bundle.py` packages only
the two CI-compiled research NROs, two required UAM DKSH shader files,
two invented 8×8 DDS images, a README and a metadata-only SHA-256
manifest into a new SD-layout ZIP. No original PS3 game files are
included by the fixed packaging path. Native GitHub Actions compile,
validate and publish that ZIP for **manual hardware testing only**.
See `docs/GPU_STAGE165_SD_RELEASE.md` for exact contents and
installation procedure. Neither C host simulation nor native NRO
cross-compilation verifies real Switch GPU presentation or original
FoJ texture/material mappings.

## Stage 166: private operator observation audit, no hardware attestation

A fixed-schema, blank-first local observation journal records the five
stage-162 screen scenarios as user-supplied declarations and tracks
initialization symptoms (including no frame, black screen and exit
behavior) separately. Optional SHA-256 binding to a locally validated
stage-165 research-only SD ZIP distinguishes binary packaging from
visual evidence. The offline tool rejects duplicate JSON fields,
out-of-order scenarios, malformed observations and mismatched bundle
hashes. Its output omits free-form private paths and never marks
hardware execution verified, even if all declared colors match the
expected sequence. Native CI publishes a blank worksheet only;
no Switch hardware or video capture is connected. Instructions:
`docs/GPU_STAGE166_HARDWARE_OBSERVATIONS.md`.

## Stage 167: shader-independent early DKSH failure colors

The optional triangle-research NRO includes a shaderless presentation
fallback for shader-code memory failures, invalid/missing vertex or
fragment DKSH modules, rejected shader layout and failed deko3d
shader-stage checks. It records two color-clear lists for the existing
swapchain buffers and attempts to present them until user exit, while
retaining a nonzero error code 6. This route is earlier than DDS
status presentation but later than device, queue, swapchain and command
buffer initialization, so not all black screens are diagnosed.
The host regression covers fixed status colors and 4096 synthetic
buffer-selection decisions per failure class; native CI cross-compiles
the app, **without proving physical Switch output**. Manual protocol:
`docs/GPU_STAGE167_DKSH_BOOT_SCREENS.md`.

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
