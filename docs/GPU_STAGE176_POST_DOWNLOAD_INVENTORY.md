# Stage 176 — descriptor-anchored downloaded artifact inventory

The stage-175 independent download check validates all five generated
NRO/DKSH binaries against the corresponding consistency receipts.
Stage 176 tightens its filesystem handling.

The inventory walker now opens the root directory with `O_DIRECTORY`
and `O_NOFOLLOW`, then descends through child directories relative
to an existing directory descriptor. It compares each child directory's
observed device and inode before and after opening, and rejects links,
special files, unknown paths and extra entries.

Once the binary, ZIP, and receipt recheck finishes, the tool also
re-enumerates the exact permitted inventory and re-reads the final
five-binary receipt. This catches ordinary files added or changed
while checks are running, instead of accepting a previously checked
directory listing as permanently valid.

Two additional generated-only regressions introduce a file or change
the receipt mid-audit and require rejection.

Run:

    python3 -m unittest discover -s tests \
      -p 'test_foj_stage175_downloaded_artifact_audit.py' -v

This improves local consistency but is not an atomic filesystem
snapshot and does not defeat an adversary with complete control of
the filesystem, malicious ABA swaps or colluding forged receipts.

**No original game assets are uploaded and no physical Switch
execution or GPU scanout is verified.**
