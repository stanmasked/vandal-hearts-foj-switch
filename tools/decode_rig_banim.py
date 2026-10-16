#!/usr/bin/env python3
"""Read verified FoJ BMODEL rigs (0x0A) and BANIM keyframes.

Based on inspection of the user's own NPEB00148 game data:
 - 89 BMODEL files contain 2,512 bone records; 494 contain only 0x0C.
 - all 450 BANIM files decode into 16,631 tracks and 1,274,805 keys.

Parsers read in-memory bytes, and never emit protected animations or assets.
Interpolation here is a research approximation, not proven FoJ game behavior.
No original game data is embedded in this source.
"""
from __future__ import annotations

from dataclasses import dataclass
import bisect
import math
import struct

MAX_BONES = 256
MAX_CLIP_BYTES = 16_000_000
MAX_TRACKS = 512
MAX_KEYS_PER_TRACK = 4096
MAX_TOTAL_KEYS = 2_000_000

Quat = tuple[float, float, float, float]
Vec3 = tuple[float, float, float]


class RigAnimationError(ValueError):
    pass


@dataclass(frozen=True)
class Bone:
    parent: int | None
    metadata: int
    rotation_xyzw: Quat
    translation_xyz: Vec3


@dataclass(frozen=True)
class Skeleton:
    bones: tuple[Bone, ...]

    def summary(self) -> dict:
        return {
            "bone_count": len(self.bones),
            "root_count": sum(b.parent is None for b in self.bones),
            "metadata_counts": {
                str(key): sum(b.metadata == key for b in self.bones)
                for key in sorted({b.metadata for b in self.bones})
            },
        }


@dataclass(frozen=True)
class Key:
    time: float
    rotation_xyzw: Quat
    translation_xyz: Vec3


@dataclass(frozen=True)
class Track:
    parent: int | None
    key_count: int
    first_time: float
    last_time: float
    keys: tuple[Key, ...]  # empty when retain_keys=False


@dataclass(frozen=True)
class Clip:
    duration: float
    tracks: tuple[Track, ...]
    key_count: int
    retained: bool

    def summary(self) -> dict:
        starts = [t.first_time for t in self.tracks]
        ends = [t.last_time for t in self.tracks]
        return {
            "duration_seconds": round(self.duration, 6),
            "track_count": len(self.tracks),
            "total_key_count": self.key_count,
            "minimum_key_time": round(min(starts), 6),
            "maximum_key_time": round(max(ends), 6),
            "track_key_counts": dict(sorted(
                (str(n), sum(t.key_count == n for t in self.tracks))
                for n in {t.key_count for t in self.tracks}
            )),
            "root_track_count": sum(t.parent is None for t in self.tracks),
            "notice": "Quaternion + XYZ track structure verified; engine pose application not yet.",
        }


def _unit_quaternion(q: Quat) -> bool:
    return all(math.isfinite(v) for v in q) and abs(sum(v*v for v in q) - 1) <= 0.04


def parse_bmodel_rig(footer: bytes) -> Skeleton:
    """Footer starts *after* geometry and material bundles.

    0x0C alone represents no embedded rig. Otherwise layout:
    0x0A + count(u16 BE) + count * (parent:u16 BE, flag:u16 BE,
    quaternion:4xf32 BE, translation:3xf32 BE) + 0x0C.
    """
    if footer == b"\x0c":
        return Skeleton(())
    if not footer or footer[0] != 0x0a or len(footer) < 36:
        raise RigAnimationError("Unsupported BMODEL rig footer")
    count = int.from_bytes(footer[1:3], "big")
    if not 1 <= count <= MAX_BONES or len(footer) != 4 + 32 * count:
        raise RigAnimationError("Invalid rig bone count/byte length")
    if footer[-1] != 0x0c:
        raise RigAnimationError("Missing BMODEL rig footer terminator")

    bones = []
    for index in range(count):
        pos = 3 + 32 * index
        parent_index, meta = struct.unpack_from(">HH", footer, pos)
        q = struct.unpack_from(">4f", footer, pos + 4)
        translation = struct.unpack_from(">3f", footer, pos + 20)
        parent = None if parent_index == 0xffff else parent_index
        if parent is not None and parent >= index:
            raise RigAnimationError("Invalid/non-ancestral rig parent index")
        if not _unit_quaternion(q) or not all(
            math.isfinite(v) and abs(v) < 1_000_000 for v in translation
        ):
            raise RigAnimationError("Invalid rig rotation/translation")
        bones.append(Bone(parent, meta, q, translation))
    if bones[0].parent is not None:
        raise RigAnimationError("First rig bone must be a root")
    return Skeleton(tuple(bones))


def parse_banim(data: bytes, *, retain_keys: bool = False) -> Clip:
    """Little-endian BANIM; track parent indices are little-endian u16.

    0x0D + duration(f32 LE) + track_count(u32 LE) + reserved(u16 LE == 0)
    track: 0x11 + parent(u16 LE) + keys(u16 LE)
    key: 0x12 + (time, quat_xyzw, translation_xyz) [8 x f32 LE]
    final terminator: 0x13
    """
    if not isinstance(data, bytes) or not 17 <= len(data) <= MAX_CLIP_BYTES:
        raise RigAnimationError("Missing or oversized BANIM")
    if data[0] != 0x0d or data[-1] != 0x13:
        raise RigAnimationError("Invalid BANIM markers")
    duration, track_count, reserved = struct.unpack_from("<fIH", data, 1)
    if (not math.isfinite(duration) or duration < 0 or duration > 600 or
        not 1 <= track_count <= MAX_TRACKS or reserved != 0):
        raise RigAnimationError("Invalid BANIM header")

    tracks = []
    position = 11
    total_keys = 0
    for track_index in range(track_count):
        if position + 5 > len(data) - 1 or data[position] != 0x11:
            raise RigAnimationError("Truncated/missing BANIM track marker")
        raw_parent, n = struct.unpack_from("<HH", data, position + 1)
        position += 5
        parent = None if raw_parent == 0xffff else raw_parent
        if parent is not None and parent >= track_index:
            raise RigAnimationError("Invalid BANIM parent index")
        if not 1 <= n <= MAX_KEYS_PER_TRACK:
            raise RigAnimationError("Invalid BANIM frame count")
        total_keys += n
        if total_keys > MAX_TOTAL_KEYS or 33*n > len(data) - 1 - position:
            raise RigAnimationError("Truncated/oversized BANIM keyframe array")

        previous_time = float("-inf")
        first_time = last_time = 0.0
        keys = []
        for i in range(n):
            if data[position] != 0x12:
                raise RigAnimationError("Invalid BANIM keyframe marker")
            values = struct.unpack_from("<8f", data, position + 1)
            position += 33
            t = values[0]
            q = values[1:5]
            xyz = values[5:8]
            if (not math.isfinite(t) or t < -1 or t > duration + 1 or
                t + 0.0001 < previous_time or
                not _unit_quaternion(q) or
                not all(math.isfinite(v) and abs(v) < 1_000_000 for v in xyz)):
                raise RigAnimationError("Invalid BANIM keyframe time/transform")
            if i == 0:
                first_time = t
            last_time = t
            previous_time = t
            if retain_keys:
                keys.append(Key(t, q, xyz))
        tracks.append(Track(parent, n, first_time, last_time, tuple(keys)))

    if position != len(data) - 1:
        raise RigAnimationError("Unexpected trailing BANIM bytes")
    return Clip(duration, tuple(tracks), total_keys, retain_keys)


def _slerp(q0: Quat, q1: Quat, t: float) -> Quat:
    """Unit quaternion shortest-path slerp (research interpolator)."""
    dot = sum(a*b for a,b in zip(q0,q1))
    if dot < 0:
        q1 = tuple(-v for v in q1)  # type: ignore[assignment]
        dot = -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        value = tuple((1-t)*a + t*b for a,b in zip(q0,q1))
    else:
        theta = math.acos(dot)
        s = math.sin(theta)
        w0 = math.sin((1-t)*theta)/s
        w1 = math.sin(t*theta)/s
        value = tuple(w0*a + w1*b for a,b in zip(q0,q1))
    norm = math.sqrt(sum(v*v for v in value))
    return tuple(v/norm for v in value)  # type: ignore[return-value]


def sample_local_pose(clip: Clip, time_seconds: float) -> tuple[Key, ...]:
    """Sample local per-bone Q/XYZ. NOT global/model-space skinning matrices.

    Clamps to each track's first/last time independently: some real tracks
    omit the last animation tick and clips may start at a negative timestamp.
    """
    if not clip.retained or not math.isfinite(time_seconds):
        raise RigAnimationError("Retained keys and finite sample time required")
    pose = []
    for track in clip.tracks:
        keyframes = track.keys
        if time_seconds <= keyframes[0].time:
            k = keyframes[0]
            pose.append(Key(time_seconds, k.rotation_xyzw, k.translation_xyz))
        elif time_seconds >= keyframes[-1].time:
            k = keyframes[-1]
            pose.append(Key(time_seconds, k.rotation_xyzw, k.translation_xyz))
        else:
            times = [k.time for k in keyframes]
            i = bisect.bisect_right(times, time_seconds) - 1
            before, after = keyframes[i], keyframes[i+1]
            span = after.time - before.time
            factor = (time_seconds - before.time)/span if span > 0 else 0
            q = _slerp(before.rotation_xyzw, after.rotation_xyzw, factor)
            xyz = tuple((1-factor)*a + factor*b
                        for a,b in zip(before.translation_xyz, after.translation_xyz))
            pose.append(Key(time_seconds, q, xyz))
    return tuple(pose)
