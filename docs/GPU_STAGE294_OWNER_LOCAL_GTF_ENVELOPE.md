# Stage294 — owner-local GTF-like layout envelope consistency

**Builds upon** [Stage293 PR #178](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/178), which proved an invented BGRA conversion actually reached the NeXium GPU. Stage294 does **not** extend the supported original game asset formats; instead it identifies exactly what would need to be proven before such a conversion can be permitted.

## Scope

The owner chooses **one already extracted local file** for read-only inspection. Only the first 128 bytes are read twice from an anchored, no-symlink file descriptor. Source data may reside anywhere outside GitHub; it is never copied or modified by this module.

```bash
python3 -m tools.foj_stage294_owner_local_gtf_envelope \
  --source-root /LOCAL/EXTRACTED/ROOT \
  --relative-file RELATIVE/TO/ROOT/texture_candidate.bin
```

The command prints a single JSON object with **booleans and categories only**. It reveals neither source names, paths, raw dimensions, internal source offsets, checksums nor bytes. Errors also avoid disclosing sensitive identifiers. It uses Stage291's candidate classification and then tests a single, **hypothetical**, little-documented `02 00 01 01` *big-endian header* layout:

- Candidate header: exactly one 2D non-cube image, bounded aligned offset and declared payload range.
- Image shape: descending integer mip levels, rejecting a chain longer than geometric dimensions allow.
- Tight contiguous payload **hypothesis**: expected byte count for RGBA8 or BC1/BC2/BC3 at each mip, including sub-4×4 BCn tails.
- Base pitch **hypothesis**: `width*4` for linear RGBA8, or compressed block-row pitch.
- Exact-file-end **hypothesis**: claimed payload end matches the physical file length (trailing container data is not silently ignored).
- Native atlas gating: width 8–256 divisible by 8, height 1–256 (multiple of 4 for BCn), at most 9 mips, and native-supported RGBA8/BC1/BC3 only.
- Reject nonlinear layouts, unclassified formats, BC2, out-of-range sizes or conflicting pitch/payload claims.

Even if **all booleans are true**, the strongest possible decision is `candidate_envelope_consistent_under_unverified_hypothesis`. Source format verification, original FoJ material mapping and game-resource conversion authorization are **always false**. No PS3 texture pixels are read or decoded; no DDS is created.

This is intentionally *not* an RSX/GTF definitive parser. The actual source may use an entirely different descriptor layout, padding, texture swizzle, compression, endian arrangement or multi-resource container. Stage292 fixtures carry a synthetic-only tag that is explicitly reported, not interpreted as original game data.

### Acceptance

The workflow runs 27 synthetic regressions with Python 3.11 and 3.13, covering consistent/contradictory source hypotheses, odd mip sizes, BCn tails, format support, trailing container bytes, malformed inputs and local no-follow/path-escape protection. Original PS3 PKGs or their extracted resources are never sent to public GitHub Actions, and there are no output artifact uploads.

**Next decision point:** review this *local-only* metadata (if an actual PS3 candidate becomes accessible in a private runtime); confirm genuine format through independent source-specific evidence before implementing any non-synthetic decoding. NeXium on synthetic materials is already covered by Stage293, not proof of original-game readiness.
