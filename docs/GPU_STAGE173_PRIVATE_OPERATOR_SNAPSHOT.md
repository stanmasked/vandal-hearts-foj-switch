# Stage 173 — descriptor-bound private operator JSON inputs

**Research only: no real Nintendo Switch execution, GPU scanout,
original FoJ assets or gameplay have been verified.**

Stage 172 hardened the generated research **build receipt**, but two
separate private operator documents still used pathname-based
`stat()/open()` checks: the stage-166 GPU observation ledger and the
stage-170 manual CPU-to-visual scenario link.

Stage 173 adds `tools/foj_stage173_private_json_snapshot.py` and
uses it in both `read_ledger()` and `read_link()`, without changing
the JSON schemas, CLI switches or operator evidence classifications.

The new reader:
- Requires a bounded regular file and fails closed if `O_NOFOLLOW`
  support is unavailable.
- Opens the final component once using no-follow/nonblocking flags.
- Compares device, inode, mode, size, nanosecond modification and
  change times before opening, after opening, after reading, and for
  the final named file.
- Double-reads up to the format-specific limit from one descriptor
  and rejects differing content or unexpected byte counts.
- Emits generic errors without file contents or private pathname
  details. Existing duplicate-key, non-finite-JSON and schema
  validation remains in each reader.

The ledger retains its 64 KiB ceiling; the explicit visual-link form
retains its 2 KiB ceiling.

## Synthetic regressions

Run from the repository root:

    python3 -m unittest discover -s tests \
      -p 'test_foj_stage173_private_json_snapshot.py' -v

Tests cover valid blank forms, direct symlinks, FIFOs, regular-file
replacement before/after open, same-inode edit between read passes,
oversize files and invalid or duplicate-key JSON. Every visual or
hardware-related statement in the fixture is deliberately invented.

The generic research workflow runs the full test discovery; the
texture and native-GPU workflows additionally run this module
explicitly. These CI checks exercise ordinary Linux filesystem
behavior. They are **not** physical console tests.

## Threat-model limitations

This is a local consistency check, not an operator signature or
attestation. It does not atomically freeze ancestor directories,
prove against malicious concurrent ABA rewrites, authenticate the
filesystem or GitHub environment, or prove a specific NRO was
loaded on real hardware.

See also [stage 171 build receipt](GPU_STAGE171_BUILD_IDENTITY.md)
and [stage 172 receipt snapshot](GPU_STAGE172_RECEIPT_DESCRIPTOR_SNAPSHOT.md).
