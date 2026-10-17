# Stage 175 — fifth DKSH and independently downloaded artifact audit

**Research-only:** no physical Nintendo Switch execution or GPU scanout
has been verified. No original *Vandal Hearts: Flames of Judgment*
resources are supplied to GitHub Actions.

Stage 174 checked that four native NRO/DKSH files matched the fixed
generated stage-165 SD ZIP, immediately before uploading the CI
artifact. A fifth generated shader, `gpu/build/foj_actor.frag.dksh`,
was published separately but was not part of that four-member ZIP.

Stage 175 deliberately keeps the stage-165 ZIP/receipt **unchanged**.
It adds a separate five-binary consistency receipt:

    build/foj-stage175-five-binary-receipt.json

The receipt contains five SHA-256 hashes, the declared commit and
Actions run ID, the validated ZIP digest, and explicit false hardware,
GPU, original-game-content and gameplay verification flags.

## Independent download path

The native `devkitA64` job now performs the stage-174 pre-upload gate,
then records the extra DKSH and rechecks its four previous hashes.
It uploads the stage-175 receipt alongside the generated files.

A **separate Ubuntu runner job**, `downloaded-audit`, is blocked
until the native job succeeds. It uses `actions/download-artifact@v4`
to download `foj-gpu-native-research` and then executes:

    python3 -m tools.foj_stage175_downloaded_artifact_audit \
      --artifact-root audit-artifact \
      --expected-commit "$GITHUB_SHA" \
      --expected-run-id "$GITHUB_RUN_ID" \
      --verify-downloaded

It checks the download as an independent local input, not by trusting
the original build directory. It:

- Rejects unknown files, missing files, unexpected directories and
  symbolic links (fixed, bounded artifact inventory).
- Revalidates stage-171 receipt, generated SD ZIP and all four
  stage-174 loose NRO/DKSH comparisons.
- Rejects changes to the stage-174 consistency report.
- Independently validates and hashes the fifth fragment DKSH.
- Compares all five hashes against the new stage-175 receipt.
- Requires the publicly uploaded operator observation worksheet to
  remain **blank**; no user-observed screen descriptions may be
  silently published.
- Requires exact agreement with the declared CI commit and run ID.

The fifth DKSH is **not** claimed to be inside the stage-165 ZIP.
Its SHA-256 is bound only by the separate stage-175 published-file
receipt. This separation preserves compatibility with prior SD bundles.

## Tests

    python3 -m unittest discover -s tests \
      -p 'test_foj_stage175_downloaded_artifact_audit.py' -v

Eleven generated-only regressions exercise a correct download,
altered/missing/symlinked fifth DKSH, changed receipts,
incorrect CI identity, duplicate JSON keys, unexpected files,
a filled observation form, exclusive receipt creation and CLI flow.

## Limits

A successful independent download verifies byte-level consistency of
the *supplied* GitHub Actions artifact against unsigned receipts
created by the same workflow. It does not independently authenticate
GitHub, defend against a malicious actor controlling both binaries and
receipts, or establish that a user later downloaded identical bytes.

It does **not** prove a physical Switch ran any NRO or that deko3d
rendered pixels. Only subsequent real-device evidence could support
those claims.

See [stage 174 pre-upload audit](GPU_STAGE174_NATIVE_ARTIFACT_COHERENCE.md)
and [stage 171 ZIP receipt](GPU_STAGE171_BUILD_IDENTITY.md).
