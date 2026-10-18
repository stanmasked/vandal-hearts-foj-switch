# Stage 176 — FD-anchored pre/post download inventory snapshots

**Generated-only research:** no original *Vandal Hearts: Flames of
Judgment* assets are collected, and neither physical Switch execution
nor GPU scanout is verified.

The stage-175 independently downloaded artifact verifier already
rechecks the ZIP, five loose NRO/DKSH binaries and three JSON receipts,
rejects unexpected paths and insists on a blank operator observation
form. However, its first directory inventory and subsequent file
reads were separate operations. A concurrent replacement of a file or
directory between these steps could undermine the inventory claim.

Stage 176 adds `tools/foj_stage176_fd_inventory_snapshot.py` and
uses `snapshot_inventory` both **before** and **after** complete
stage-175 receipt and binary validation.

The inventory traversal:

- Requires a real directory root; rejects a symlink root.
- Opens every subdirectory by `O_DIRECTORY | O_NOFOLLOW` relative
  to a held parent directory descriptor.
- Enumerates each directory through an independently opened
  `.` descriptor, avoiding shared readdir cursor state between
  snapshots.
- Rejects unexpected names, files, folders, symlinks, special files,
  duplicates and excess entries (24 names / 4096 name bytes).
- Checks directory identity and metadata before and after traversal,
  including device/inode, type, size, mtime and ctime.
- Records exact metadata of every expected file and directory. The
  audit fails unless the complete first and second inventories match.

The downloaded job now refuses a result even if all file SHA-256
digests agree **when the inventory changed during the audit**. This
protects against typical simultaneous renames/replacements and
in-place file metadata edits; it does not promise transactional
filesystem semantics.

## Synthetic regressions

    python3 -m unittest discover -s tests \
      -p 'test_foj_stage176_fd_inventory_snapshot.py' -v

The six new regressions cover repeated stable scans, a same-name
metadata change, root and child symlinks, missing/extra/FIFO files,
a replaced child directory after content verification, and a
same-content file modification between snapshots.

Both the devkitA64 native-build job and the independent Ubuntu
download-check job run these regressions. Existing stage-175 JSON and
binary report schemas are unchanged.

## Scope and limitations

Stage 176 is an **unsigned local consistency check** for the
previously downloaded generated research artifact. A hostile
filesystem could still perform exactly timed ABA rewrites between
scans, fabricate metadata, or modify bytes after verification.
Nothing here authenticates the user, GitHub, or the eventual SD-card
copy. Verifying a build's files is not evidence that a Switch loaded
them or rendered any frame.

See [stage 175 downloaded artifact audit](GPU_STAGE175_DOWNLOADED_ARTIFACT_AUDIT.md).
