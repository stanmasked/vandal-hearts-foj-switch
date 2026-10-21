# Stage290 — owner-local format compatibility triage (not PS3 decoding)

**Based on:** [Stage289 PR #174](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/174), which hardened the publication of actual synthetic NeXium GPU captures.

## Objective

Stop confusing a possible DDS signature inside a game container with a native-loadable DDS file. Before any private material mapping, distinguish:

- file-start DDS accepted **byte-for-byte** by the current Switch `gpu/atlas_dds.c` intake (RGBA8, BGRA8, BC1/DXT1, BC3/DXT5, strict geometry/mips/size/caps);
- classic DDS signatures with unsupported headers or trailing container bytes;
- embedded DDS-looking sequences which are **not** directly loadable files;
- skipped large files or incomplete enumeration (never misreported as proof of absence);
- raw RGBA8/BGRA8 candidates whose alpha channels are completely opaque and therefore *eligible in principle* for the conservative Stage286 rear slot.

Existing reusable modules do the heavy lifting: `foj_texture_probe.inventory` inventories byte positions with bounded file-descriptor anchored reads, and `foj_gpu_local_dds_preflight.classify_classic_dds` implements the exact native acceptance contract. Stage290 independently reopens each file-start candidate, compares it to the scan metadata, reads the bytes twice from the anchored file descriptor, and classifies it without exporting file identity.

## Run **offline only** on already extracted, locally owned files

```bash
python3 -m tools.foj_stage290_private_texture_compatibility \
  --extracted-root /your/LOCAL/extracted-data \
  --max-file-mib 32 --max-files 4096
```

The argument is a **local directory**, not a PS3 PKG file and not a GitHub URL. The tool **does not decrypt PS3 packages, extract or convert textures, or upload game material**. Do not put the game package, extracted data, per-file inventory or an unsanitized report into the public repo or GitHub Actions.

Only aggregate JSON is printed: counts of scanned/skipped files, embedded headers, exact compatible DDS, incompatible DDS, format counts, rear-opaque candidates, and a completeness flag. It emits no paths, private filenames, pixels, SHA-256 hashes, or texture bytes. A linked file/directory or unsafe change is rejected without printing the sensitive path.

A nonzero `skipped_large_files` count or `file_limit_reached=true` makes `scan_complete_within_declared_limits=false`. An empty candidate count in that state is **not** evidence that no DDS is present.

## Acceptance and scope

The synthetic-only Stage290 workflow executes 15 tests under Python 3.11 and 3.13. The tests include RGBA/BGRA/BC1/BC3 acceptance, alpha eligibility, embedded DDS exclusion, malformed header rejection, extra bytes, skip/incomplete conditions, symlink rejection, bounded limits, and no private filenames in success/failure CLI output.

The Stage288/289 NeXium proof is *only* about invented DDS images. This new local classifier is **not** proof that original Vandal Hearts: Flames of Judgment uses classic DDS, that a found candidate belongs to the game, that a source maps to any actor/material slot, or that a physical Switch can render its pixels. Those claims need separate local, owner-authorized format-forensic and GPU validation.

**Historical-evidence clarification (Stage300, 2026-10-21):** Prior owner-local
research already confirmed **five actual DDS-in-`.tga` game resources**,
including BGRA8 256×256 and BC1 256×256/1024×1024. See
[REAL_RESOURCE_SIGNATURES.md](REAL_RESOURCE_SIGNATURES.md). This Stage290
classifier does not independently repeat those historical observations, nor
does that five-resource evidence establish the formats of all textures.
The 1024×1024 BC1 case exceeds the present strict 256×256 GPU loader;
see [Stage300 reconciliation](GPU_STAGE300_HISTORICAL_REAL_DDS_GAP.md).
