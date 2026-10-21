# Stage289 — public evidence publication gate for actual NeXium GPU captures

**Stack:** Stage288 [PR #173](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/173), proven on exact commit `bfc75c1d` with [three successful Stage288 jobs](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39648079093).

## Reason for this change

Stage288 correctly stages *synthetic-only* material0/1/2 DDS through Stage286 and verifies two actual NeXium screenshots. However, its original upload step had `if: always()` and sent the entire `runtime-evidence/` directory. That is an unnecessarily permissive publication boundary: an unexpected file or a failed audit could still be uploaded. Even though original PS3 assets are not present in the CI, the research pipeline must be safe by construction before an owner-local workflow ever handles private data.

## Gate

`tools/foj_stage289_public_guest_evidence.py` accepts a source evidence directory and creates a **new** publish-only directory. It:

1. Rejects unexpected source files, nested directories, symlinks, special entries, missing files, oversized evidence, or a preexisting target.
2. Independently recomputes Stage288's frame and native-witness audit and compares it to the preexisting Stage288 receipt.
3. Checks the NeXium nightly archive SHA-256 receipt syntax, without copying the binary or the guest's raw log.
4. Copies exactly nine public files: two real emulator PNGs, three generated-only origin/DDS attestation JSON receipts, two native NRO marker texts, the Stage288 recomputed audit receipt, and the NeXium archive SHA-256 receipt.
5. Re-audits the exported copy and verifies its bytes agree with the original source.
6. Makes the upload step conditional on a **successful** pipeline; uploads `runtime-evidence-public/` only, not the unrestricted source tree.

The Stage286 private binding manifest, original PS3 assets, and `guest.log` are **never public artifacts**. On failure, no public export is uploaded (diagnostics remain visible as ordinary CI logs where appropriate).

## Coverage

Eleven independent Python negative/positive tests check the allowlist, exclusion of raw logs, unexpected DDS/PKG material, symlinks, missing native receipts, spoofed audit receipts, changed DDS hashes, malformed emulator archive fingerprints, and preexisting destination refusal. These host fixtures do **not** constitute emulator proof. The Stage288 NeXium job still runs the real NRO on the actual emulator, and Stage289 gates the artifact publication after that native proof.

## Limits

This is an evidence-publishing safety improvement, **not** a claim to decode original FoJ PS3 textures, verify original material mapping, run on physical Nintendo Switch, or validate owner-private material pixels. Private PS3 assets must stay outside public GitHub Actions and repository history.
