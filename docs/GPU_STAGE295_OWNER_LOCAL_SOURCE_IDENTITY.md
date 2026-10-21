# Stage295 — private source-byte identity before PS3 texture research

**Base:** [Stage294 PR #179](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/179). Stage293 [PR #178](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/178) separately proved that **synthetic** converted textures reached real NeXium GPU frames.

## Problem addressed

A 128-byte GTF-looking prefix might belong to a file that has changed, been truncated, or been incorrectly selected. Stage294 checks a structural *hypothesis* without reading texture payloads. Stage295 adds an owner-local, read-only **whole-file, two-pass SHA-256 comparison to an independently provided private expected digest**. This creates a basic byte-identity boundary **before** any future original-asset research.

Digest comparison does **not** prove that a source came from Vandal Hearts: Flames of Judgment, uses any particular PS3 format, is decryptable, or can map to our generated actor. All these claims stay explicitly false in receipts. A digest computed from a corrupted input and then approved by the same program is not independent provenance.

## Owner-local-only operation

Keep the extracted file and the owner-held digest in separate **local directories outside the public repository**. The digest file must contain exactly 64 lowercase hexadecimal SHA-256 characters, optionally followed by a newline, with private `0600` permissions.

```bash
python3 -m tools.foj_stage295_owner_local_source_integrity \
  --source-root /private/EXTRACTED/FILES \
  --relative-file RELATIVE/TEXTURE/CANDIDATE.bin \
  --digest-root /private/INDEPENDENT-DIGESTS \
  --digest-file owner-expected.sha256
```

Obtain the expected SHA-256 **independently**, from an owner-verified source or earlier trusted local record. Do not share, commit, upload or print the private digest in CI. Supplying a hash of the same just-opened unverified file only demonstrates self-consistency, not provenance.

The gate checks that source and digest roots are separate directories, rejects linked roots/intermediate components/final files and path traversal, requires the digest file to be private, and reads both input passes through **the same anchored regular-file descriptor** in 256-KiB chunks (up to 512 MiB). It checks byte count, EOF, file identity and two digests before comparing with the owner's digest using constant-time equality. It then applies Stage294's **hypothetical prefix-only** classification to the verified source snapshot. Normal in-place edits and substitutions are detected; a privileged adversary capable of concurrent ABA rewriting is outside this guarantee.

The CLI prints **only** safe booleans, named classifications and limitations. No original file content, path, filename, exact dimensions, original SHA-256, offset, or asset identifier is emitted. The source is never decrypted, converted, copied or modified. The gate never accepts a request to upload the source or digest.

## Synthetic CI and scope

The new workflow runs the standalone Stage295 synthetic unit test module on Python 3.11 and 3.13, covering a matching known generated fixture, unknown file types, changed bytes, length mismatches, untrusted/malformed/public digests, symlinked paths, directory escape, CLI disclosure, excessive size, missing manifest and disagreement between two complete read passes.

We cannot claim an original PS3 texture was verified until an actual, independently identified FoJ asset is available **in a private authorized runtime**. Prior project references to package `NPEB00148` are not evidence of bytes currently present. In particular, the separate PS1 `.bin/.cue` files are **not** PS3 inputs. The public GitHub CI uses only invented fixtures and publishes no artifacts.

## Further decision gate

With an independently authenticated local asset and its private digest, a later *private* experiment can investigate the true GTF/RSX descriptor semantics (pitch, swizzle, endian policy and mip layout) and compare decoded pixels to another independent reference before considering real-source DDS conversion and a fresh NeXium scene. Without that evidence, retain Stage292/293 as **generated-only** GPU research.
