# Stage 174 — native loose SDK binary ↔ fixed SD ZIP coherence

**Research-only. No real Nintendo Switch GPU scanout, physical
execution, original FoJ assets or gameplay have been verified.**

The stage-171 identity receipt validates the entire fixed stage-165
generated-only SD ZIP, including exactly two NRO executables and two
DKSH shader modules. The native GitHub Actions workflow also uploads
these four SDK build outputs as **separate files**. Previously a valid
ZIP/receipt alone could not reject one of those loose outputs being
different from its corresponding ZIP member.

Stage 174 adds a strict **pre-upload** gate:

    python3 -m tools.foj_stage174_native_artifact_coherence \
      --repo-root . \
      --bundle build/foj-stage165-gpu-sd-smoke.zip \
      --receipt build/foj-stage171-ci-build-receipt.json \
      --expected-commit "$GITHUB_SHA" \
      --expected-run-id "$GITHUB_RUN_ID" \
      --output build/foj-stage174-loose-coherence.json

The tool first validates the stage-171 receipt and ZIP. The receipt
must state precisely the expected CI commit and GitHub Actions run ID.
It then checks the four **fixed** built files from stage 165:

| Loose SDK build output | ZIP member |
| --- | --- |
| `build/foj-deko3d-clear-smoke.nro` | `switch/foj/foj-deko3d-clear-smoke.nro` |
| `build/foj-deko3d-triangle-research.nro` | `switch/foj/foj-deko3d-triangle-research.nro` |
| `gpu/build/foj_actor.vert.dksh` | `switch/foj/gpu/foj_actor.vert.dksh` |
| `gpu/build/foj_triangle.frag.dksh` | `switch/foj/gpu/foj_triangle.frag.dksh` |

It rejects a mismatch, missing file, symlink or non-regular input,
invalid NRO/DKSH structure, oversized file, unexpected read length or
content change. For each loose SDK output it performs two bounded
reads from the same open descriptor, anchored to no-follow directory
descriptors. Exactly four matching SHA-256 digests are required.

Only after these checks succeed does the tool exclusively create
`foj-stage174-loose-coherence.json`. It records the four matching
SHA-256 values, declared CI identifiers, and explicit **false**
hardware/gameplay verification fields. GitHub Actions tests this gate
and includes its output in the generated-only research artifact.

There is no scanning of PS3 directories, loading of user-owned game
data or collection of real hardware observations.

## Regression testing

    python3 -m unittest discover -s tests \
      -p 'test_foj_stage174_native_artifact_coherence.py' -v

The synthetic suite checks matching fabricated binaries; modified NRO
and DKSH payloads; wrong commit/run/receipt; missing or symlinked
files; symlinked ancestor; exclusive-new report creation; and the
command-line rejection of a changed loose file before publication.

## Important limitations

This is a **consistency check immediately before upload**, not a
cryptographic signature or a verification of what GitHub later
delivered to an end user. The receipt's commit/run metadata and
environment values can be compared for consistency but this alone
does not authenticate GitHub. A malicious actor controlling all
inputs could make a self-consistent forged artifact set.

GitHub Actions also uploads an additional
`gpu/build/foj_actor.frag.dksh` module **not present in the stage-165
fixed SD ZIP**. This fifth loose file is outside this four-member ZIP
coherence gate; it is not silently claimed as checked.

Matching generated NRO/DKSH bytes does not establish that Homebrew
Menu ran them or that any GPU rendered a frame on a real Switch.
The stage-166 and stage-170 observation forms remain operator-only.
