# Stage291 — cautious PS3 texture-header triage, no decoder

**Stack:** Stage290 [Draft PR #175](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/175), exact native classic-DDS compatibility on locally extracted files. Stage289 [PR #174](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/174) independently gates public NeXium evidence.

## Why this is a separate stage

A PS3-era title does not necessarily store native DDS files. The RSX can use texture layouts unlike the plain RGBA/BGRA/BC1/BC3 DDS that our current Switch loader validates. Matching four version bytes is only a **lead**, not proof of the game's format.

Third-party references used to scope conservative *hypotheses*:
- [PS3 Developer Wiki: GTF, Graphics Texture Format](https://www.psdevwiki.com/ps3/Multimedia_Formats_and_Tools)
- [PSL1GHT RSX texture structure](https://bucanero.github.io/PSL1GHT/struct__gcmTexture.html)
- [Community CTXR/GTF converter with a specific version-0x02000101 example](https://github.com/316austin316/CTXR-Converter/blob/main/ps3_ctxr_module.py)

These are not FoJ-specific evidence and differ by variant. We therefore **do not** decrypt a package, interpret arbitrary RSX structures as textures, infer original materials, rearrange swizzled images, unpack BC formats or create converted files.

## Owner-local usage

```bash
python3 -m tools.foj_stage291_ps3_texture_header_triage \
  --extracted-root /YOUR/LOCAL/already-extracted-files \
  --max-files 4096
```

Input is a local **directory** only. No online addresses, public CI game packages, or output directories are accepted. This command never writes to the source.

Every ordinary file gets at most a 128-byte, descriptor-anchored prefix read twice. Nested directories are visited without following symlinks and with bounded depth/entries. Symlinks, special files, and observed source mutations fail closed. A finite file budget explicitly signals incompleteness; large files are not fully read.

The output is aggregate counts only: GTF-like version candidates; rejected/malformed hints; classic DDS deferred to Stage290; unrelated known image signatures; unknown/unclassified files. There are no source filenames, original offsets, source paths, hashes, image data, or private pixels in stdout/stderr or CI artifacts.

## What the GTF-like buckets actually mean

- `0x02000101`: only a narrow single-texture, bounded, big-endian candidate layout is checked. Format-byte hypotheses (RGBA/BC1/BC2/BC3) and the documented linear bit become *labels*, not conversions. A non-linear label does not prove a particular tiling/swizzle scheme.
- `0x020200ff`: only a version/count/header-offset consistency check is performed. Its texture descriptor offsets are **not** parsed with the other variant's layout.
- Other signatures, missing/malformed structure, or embedded file data: no conversion claim.
- DDS at file start: its true byte-for-byte eligibility must be evaluated separately by Stage290 and the native Switch loader.

**Conversion is blocked for every category.** The gate explicitly lists the missing proofs: exact source structure, true channel and pixel format, endian/remap policy, mip and pitch alignment, swizzle/tiling, FoJ material association, native DDS round-trip and GPU frame validation.

## Acceptance

Stage291 CI runs 20 synthetic-only Python regression tests on 3.11 and 3.13. They cover accepted *hints*, malformed versions/dimensions/offsets, unknown formats, exclusion of unrelated containers, incomplete scans, source symlinks, no private identifiers in success/failure CLI output, and conversion refusal.

Future owner-local Stage292 work may attempt a **single explicit format variant** only after real source metadata has independently established its layout. That experiment must perform a safe new-destination conversion and byte-size/alpha/mip validation before seeking a native GPU proof. Nothing here establishes that the provided NPEB00148 game actually contains GTF files.
