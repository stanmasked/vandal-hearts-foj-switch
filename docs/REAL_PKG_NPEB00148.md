# Verified NPEB00148 PS3 package intake

**Inspection date:** 2026-10-16 (UTC)  
**Evidence source:** Two user-provided binary attachments, read locally and
joined virtually in memory. The PKG was **not uploaded to GitHub**.

## Outer archive

| Field | Value |
| --- | --- |
| Part A length | 450,000,000 bytes |
| Part B length | 155,484,862 bytes |
| Joined ZIP length | 605,484,862 bytes |
| ZIP entries | 1 |
| ZIP method | STORED (0), no ZIP compression |
| Contained PKG length | 605,484,624 bytes |
| ZIP entry CRC32 | `5adf66f1` |
| Full streamed CRC32 | `5adf66f1` — **match** |
| PKG SHA-256 | `969d6213409dd0b84fa71c7a3f9e3082cbadf93c13638aa79b0b4d1615b99189` |

**ZIP entry:** `Vandal.Hearts.Flames.of.Judgement_d30n_NPEB00148.pkg`

These checks establish that the split ZIP can be reconstructed consistently
and that the uncompressed contents match the checksum stored *inside that ZIP*.
There is **no independent trusted publisher hash** for authenticity comparison.

## Plaintext PKG header (verified directly)

| Field | Value |
| --- | --- |
| Magic | `7F 50 4B 47` (`\x7fPKG`) |
| Revision | `0x0000` — **non-finalized / debug-style PKG** |
| Platform/type | `0x0001` — PlayStation 3 |
| Title ID substring | `NPEB00148` |
| Content ID | `EP0101-NPEB00148_00-VANDAL0H0BY0D30N` |
| Metadata offset | `0xC0` (192 bytes) |
| Metadata size | `0xC0` (192 bytes) |
| Metadata records | 8 |
| Declared item count | 21 |
| Declared total size | `0x2416F650` (605,484,624 bytes), **matches** |
| Encrypted-data offset | `0x180` (384 bytes) |
| Encrypted-data length | `0x2416F470` (605,484,144 bytes) |
| Data end offset | `0x2416F5F0` (605,484,528 bytes) |
| Remaining trailer | 96 bytes |

### Metadata entry summary

The plaintext metadata contains these public-format records (id and byte size):

| Record ID | Length | Interpreted public-format field |
| --- | ---: | --- |
| 1 | 4 | DRM type = 3 |
| 2 | 4 | Content type = 5 |
| 3 | 4 | Package flags/value = 78 (`0x4E`) |
| 4 | 8 | Package data-size field = 605,484,144 |
| 5 | 4 | Package builder/version field (not decoded further) |
| 7 | 24 | Digest-related structure; raw payload **omitted** |
| 8 | 8 | Package metadata field; raw payload **omitted** |
| 9 | 8 | Package metadata field; raw payload **omitted** |

Interpretations of the fields are from the public PS3 PKG format schema;
the existence, types and lengths of these records were confirmed by inspection.
See https://www.psdevwiki.com/ps3/PKG_files .

## Key discovery and boundaries

Revision `0x0000` is **not** the standard finalized retail PKG revision
(`0x8000`); this package could be a debug-style rebuild/repack. File naming
alone is not a guarantee of original publisher provenance.

**What is verified:** valid PKG magic and structural bounds; correct PS3
platform field; the NPEB00148 content ID; contiguous plaintext metadata;
the encrypted section declared in the header; the archive's CRC and full-file
SHA-256.

**What is not verified:** that this is an official Konami publisher build;
availability of unencrypted models, textures, audio, `EBOOT.BIN`,
`PARAM.SFO`, game logic, or legal access to any protected content;
the ability to run the original code on Switch.

This initial inspection **did not extract or decrypt** the package payload.
The data region is designated encrypted according to the PKG format. The
number of entries is read from the plaintext header, **not** from a decoded
item table. No cryptographic keys, license files, executables, or assets were
published.

## Follow-up gates

1. Retain this report as the Gate 0 baseline and keep the PKG local.
2. Identify which assets are lawfully accessible using locally available
   authorized tools, without assuming the contents of encrypted records.
3. Confirm original engine and resource formats using actual evidence.
4. Compare source-port feasibility with clean-room recreation strategy.
5. Keep native Switch synthetic probes and original-game progress tracked
   separately.

`tools/inspect_split_pkg.py` can regenerate a comparable report from the
locally held split archive without extracting files to disk.
