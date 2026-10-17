# Stage 172 — stable descriptor snapshot for unsigned build receipt

**Research-only. No physical Nintendo Switch launch or GPU scanout has
been verified. No commercial PS3 game content is included.**

Stage 171 binds the SHA-256 of a generated research SD ZIP, two NRO
files and two DKSH shader binaries to a declared CI commit/run ID.
However, its offline \`read_receipt()\` previously checked the named
JSON's metadata with \`lstat()\` and then followed the pathname with
\`Path.open()\`. A local filesystem change could replace the file
between those operations, causing the parser to accept a different
inode from the one whose size and type were checked.

Stage 172 strengthens receipt input without changing the schema or the
published stage-171 CI artifact:

1. Reject non-regular and out-of-bounds named files before opening.
2. Open once with \`O_NOFOLLOW\` and \`O_NONBLOCK\` when available.
3. Compare device, inode, mode, size, nanosecond modification and
   change times for the named file, opened descriptor, post-read
   descriptor, and final named file.
4. Read no more than \`MAX_RECEIPT + 1\` bytes on two passes through the
   same opened descriptor. Require equal content and exactly the
   initially recorded byte length.
5. Parse UTF-8 JSON with duplicate keys and non-finite constants
   rejected. Retain strict stage-171 field/schema and checksum validation.
6. Fail closed with a generic error; do not print private input paths.

## Tests

The existing \`tests/test_foj_stage171_build_identity.py\` suite is
extended with adversarial checks for:

- A symlink substituted between \`lstat()\` and \`os.open()\`.
- A different *regular file* substituted just before \`os.open()\`.
- A different *regular file* substituted just after descriptor open.
- Same-inode, same-length JSON changed between the two descriptor reads.
- A named FIFO, rejected without waiting for a writer.

Run the regression suite:

    python3 -m unittest discover -s tests \
      -p 'test_foj_stage171_build_identity.py' -v

The existing research and native workflows already run this test
module when it changes. A successful Linux test run indicates this
specific local race/failure-handling logic works on the CI filesystem,
**not** that CI receipts are cryptographically authenticated or that
a real Switch executed any NRO.

## Limits

Receipt JSON is still **unsigned**. A malicious actor controlling
*both* the archive and receipt can forge a self-consistent declaration.
The supplied GitHub commit/run values remain declarations, not
automatically verified against GitHub's authenticated API.

This protects the final pathname/descriptor checks on supported local
filesystems; it does not guarantee safety under malicious ancestor
directory swaps, remote or adversarial filesystems, or an actor
controlling the interpreter itself. It does not prove the user loaded
or ran the matching binary.

The command line and receipt format remain those described in
[stage 171](GPU_STAGE171_BUILD_IDENTITY.md).
