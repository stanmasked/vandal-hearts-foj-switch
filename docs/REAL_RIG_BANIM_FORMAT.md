# Original FoJ skeletal rig and BANIM keyframe format

**Verified 2026-10-16**, using the user's original `NPEB00148` PS3
debug-style package → `cdata.psarc`. The repository contains parsers,
synthetic test fixtures and aggregate findings, **not original game assets**.

## Structural validation across the complete game archive

| Category | Verified |
| --- | ---: |
| BMODEL total | 583 |
| BMODEL with a populated skeleton block | **89** |
| BMODEL without a skeleton block | **494** |
| Bone records across all skeletons | **2,512** |
| BANIM files parsed fully | **450 / 450** |
| Animation bone tracks | **16,631** |
| Actual keyframes | **1,274,805** |
| Zero-duration, single-frame object animations | **3** |
| Malformed keyframe/parent/timestamp/rotation records | **0** |

One multi-root skeleton (`bridge_gear.bmodel`) has two root nodes;
the other 88 rigged models have one root. Multiple roots must be supported.

The original files were structurally checked with independent local
readers. GitHub Actions tests the implementation with generated fixtures,
not the copyrighted 605 MB archive.

## BMODEL 0x0A skeleton footer — big-endian

After the last mesh section and the material table:

| Bytes | Meaning |
| --- | --- |
| `0A` | Skeleton-table start |
| 2 bytes, BE | Number of bones `N` |
| `N × 32` bytes | Fixed-size bone records |
| `0C` | Ending marker |

Each **32-byte bone record** contains:

| Bytes | Parsed field |
| --- | --- |
| 0–1 | Parent bone index, uint16 BE (`FFFF` = no parent) |
| 2–3 | Additional uint16 BE metadata (observed values 0–6; purpose unknown) |
| 4–19 | Four float32 **BE quaternion XYZW** components |
| 20–31 | Three float32 **BE translation XYZ** components |

All 2,512 quaternions have approximately unit length, and all parent
references point to earlier records. A 494-file subset instead ends
immediately with only the one-byte `0C` terminator, without a rig.

The position fields are **local transform candidates**; world-space
composition, bone rest-pose correction and inverse bind matrices are not yet
confirmed from original runtime behavior.

## BANIM format — little-endian

Unlike BMODEL geometry and rig records, BANIM data uses **little-endian**
numeric fields.

| Block | Representation |
| --- | --- |
| File header | `0D`, duration (f32 LE), track count (u32 LE), 2-byte reserved zero |
| Track header | `11`, parent track index (u16 LE; `FFFF` = root), key count (u16 LE) |
| Keyframe | `12`, followed by 8 float32 LE values |
| File ending | `13` |

Each **33-byte keyframe** contains the timestamp, a quaternion XYZW and
a translation XYZ. Its float order is:

`time, qx, qy, qz, qw, tx, ty, tz`.

All 1,274,805 original frames validate for marker placement, finite
values, near-unit quaternion length, monotonically increasing timestamps
and in-file bounds. The greatest measured deviation of squared quaternion
length from 1 in these clips was below `9e-8`.

**Important exceptions:**

- Three environmental object clips have duration 0 and one key. They are
  valid data, not malformed headers.
- Different tracks within one clip can contain different numbers of keys.
- Some time sequences begin at negative time (down to about −0.066667 s).
- A track's last key can precede the clip duration by up to ~0.066667 s.
  Do not require `key_count = duration × 30 + 1` or uniform track lengths.

## Working research code

- [Pure Python rig and BANIM parser plus local pose sampling](../tools/decode_rig_banim.py)
- [Native C BANIM parser and quaternion slerp](../core/banim_core.c)
- [Complete local-only audit](../tools/audit_rig_anims.py)
- [Optional export of one selected, user-owned BANIM](../tools/export_local_banim.py)
- [Native Switch BANIM inspection app](../switch/source/banim_main.c)

The Python and native C local-pose interpolators use shortest-path
quaternion SLERP and linear translation. **This interpolation is an
independent research implementation**, not yet proven to reproduce the
PS3 engine's animation blending or sampling behavior.

Reproduce the all-files audit privately:

```sh
python3 -m tools.audit_rig_anims \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" > local-rig-animation-audit.json
```

This report exports aggregate counts only. No original transform values,
full motion files or commercial geometry are published.

## Outstanding steps before animated original-game graphics

1. Correlate model rig indices and each BANIM's track identities.
2. Confirm pose composition, coordinate handedness and inverse bind pose.
3. Implement CPU/GPU skin matrices and weighted vertex deformation.
4. Validate at least one user-owned animated model on desktop and Switch.
5. Reimplement material rendering and original events/combat systems.

**The animation file format is now structurally decoded. A playable,
animated Vandal Hearts: Flames of Judgment port is not yet running.**
