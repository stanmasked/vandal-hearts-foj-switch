"""Synthetic multi-frame BANIM-to-skinning C/Python consistency oracle.

C under test uses the actual production foj_banim_sample(),
foj_skin_sample_palette() and foj_skin_deform(). The independent
reference samples invented keyframes in Python and reuses the independent
quaternion-geometry oracle from Stage 190, not C's matrix arithmetic.
"""
from __future__ import annotations

import math
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_foj_stage190_skin_matrix_contract import (
    IDENTITY, Q, bone, vertex, expected
)

ROOT = Path(__file__).resolve().parents[1]
TIMES = (-0.5, 0.0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5)


def key(t, q, xyz):
    return (float(t), tuple(q), tuple(xyz))


def interpolated(q0, q1, alpha):
    """Quaternion shortest-arc slerp independent of production C."""
    q0 = tuple(float(x) for x in q0)
    q1 = tuple(float(x) for x in q1)
    dot = sum(a*b for a, b in zip(q0, q1, strict=True))
    if dot < 0:
        q1 = tuple(-x for x in q1)
        dot = -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        mixed = tuple((1-alpha)*a + alpha*b
                      for a, b in zip(q0, q1, strict=True))
    else:
        theta = math.acos(dot)
        theta_sine = math.sin(theta)
        a = math.sin((1-alpha)*theta)/theta_sine
        b = math.sin(alpha*theta)/theta_sine
        mixed = tuple(a*x+b*y for x, y in zip(q0, q1, strict=True))
    norm = math.sqrt(sum(x*x for x in mixed))
    return tuple(x/norm for x in mixed)


def sample_track(track, when):
    """Track-local clamping; linear XYZ plus shortest-arc XYZW."""
    if not track:
        raise ValueError("Empty synthetic track")
    if when <= track[0][0]:
        return track[0][1:]
    if when >= track[-1][0]:
        return track[-1][1:]
    for left, right in zip(track, track[1:]):
        if left[0] <= when < right[0]:
            alpha = (when-left[0])/(right[0]-left[0])
            q = interpolated(left[1], right[1], alpha)
            pos = tuple((1-alpha)*x + alpha*y
                        for x, y in zip(left[2], right[2], strict=True))
            return q, pos
    raise ValueError("Missing track interpolation interval")


def fixture():
    bind = [
        bone(-1, 2, 1, 0),
        bone(0, 0, 2, 0),
        bone(-1, -4, 0, 1),
    ]
    tracks = [
        [
            key(0, IDENTITY, (2, 1, 0)),
            key(0.5, (0, 0, Q, Q), (3, 1, 0)),
            key(1, (0, 0, 1, 0), (4, 1, 0)),
        ],
        [
            key(0.25, IDENTITY, (0, 2, 0)),
            key(0.75, (Q, 0, 0, Q), (0, 3, 0)),
        ],
        [
            key(0, IDENTITY, (-4, 0, 1)),
            key(1, (0, 0, 0, -1), (-3, 0, 1)),
        ],
    ]
    vertices = [
        vertex(3, 1, 0, (0, 1)),
        vertex(3, 3, 0, (1, 1)),
        vertex(-4, 0, 1, (2, 1)),
        vertex(4, 3, 0, (0, 0.25), (1, 0.75)),
    ]
    return bind, tracks, vertices


def predict(t):
    bind, tracks, vertices = fixture()
    sampled = [
        (b[0], *sample_track(tracks[i], t))
        for i, b in enumerate(bind)
    ]
    # expected() independently composes local quaternion poses into
    # world transforms, and then applies inverse bind + weighted points.
    return expected(bind, sampled, vertices)


def parse_frames(stdout):
    lines = iter(stdout.splitlines())
    frames = []
    for header in lines:
        parts = header.split()
        if len(parts) != 5 or parts[0] != "FRAME":
            raise ValueError("Invalid frame record")
        try:
            frame_id, time, bones, vertices = (
                int(parts[1]), float(parts[2]),
                int(parts[3]), int(parts[4])
            )
        except ValueError as exc:
            raise ValueError("Invalid frame metadata") from exc
        if frame_id != len(frames) or frame_id >= len(TIMES):
            raise ValueError("Unexpected, duplicate or excessive frame ID")
        if not math.isfinite(time) or abs(time-TIMES[frame_id]) > 1e-6:
            raise ValueError("Wrong frame sampling time")
        if bones != 3 or vertices != 4:
            raise ValueError("Wrong synthetic frame dimensions")
        def record(label, count):
            fields = next(lines).split()
            if len(fields) != count+1 or fields[0] != label:
                raise ValueError("Malformed native C matrix/vertex record")
            result = tuple(float(x) for x in fields[1:])
            if not all(math.isfinite(x) for x in result):
                raise ValueError("Non-finite native output")
            return result
        matrices = tuple(record("M", 12) for _ in range(bones))
        deformed = tuple(record("V", 3) for _ in range(vertices))
        if next(lines) != "END":
            raise ValueError("Frame terminator missing")
        frames.append((time, matrices, deformed))
    if len(frames) != len(TIMES):
        raise ValueError("Incomplete native animation timeline")
    return frames


class Stage191ContinuousAnimationOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        path = str(Path(cls.tmp.name)/"foj_stage191_probe")
        subprocess.run(
            ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-pedantic", "-Icore",
             "tools/foj_stage191_multiframe_skin_probe.c",
             "core/banim_core.c", "core/skeletal_skin.c", "-lm",
             "-o", path],
            cwd=ROOT, capture_output=True, text=True, check=True,
            timeout=30,
        )
        run = subprocess.run(
            [path], cwd=ROOT, capture_output=True, text=True,
            check=True, timeout=10,
        )
        cls.native_stdout = run.stdout
        cls.frames = parse_frames(run.stdout)

    def assert_components(self, actual, truth, tolerance=0.0005):
        self.assertEqual(len(actual), len(truth))
        for idx, (got, want) in enumerate(zip(actual, truth, strict=True)):
            self.assertEqual(len(got), len(want))
            for component, (x, y) in enumerate(zip(got, want, strict=True)):
                self.assertAlmostEqual(
                    x, y, delta=tolerance,
                    msg=f"entry={idx} component={component}")

    def test_all_eight_times_match_independent_quaternion_math(self):
        self.assertEqual(len(self.frames), 8)
        for i, (time, matrices, vertices) in enumerate(self.frames):
            with self.subTest(t=time):
                self.assertEqual(time, TIMES[i])
                oracle_matrices, oracle_vertices = predict(time)
                self.assert_components(matrices, oracle_matrices)
                self.assert_components(vertices, oracle_vertices)

    def test_pre_start_clamped_to_first_key(self):
        self.assert_components(self.frames[0][1], self.frames[1][1])
        self.assert_components(self.frames[0][2], self.frames[1][2])

    def test_post_end_clamped_to_last_key(self):
        self.assert_components(self.frames[-1][1], self.frames[-2][1])
        self.assert_components(self.frames[-1][2], self.frames[-2][2])

    def test_child_track_stays_at_first_key_before_quarter_second(self):
        # The child starts at 0.25s; its *local* key is clamped, while
        # root motion may already change world output at t=.125.
        bind, tracks, vertices = fixture()
        self.assertEqual(sample_track(tracks[1], 0),
                         sample_track(tracks[1], 0.125))
        self.assertGreater(
            sum(abs(a-b) for a,b in zip(self.frames[1][2][1],
                                       self.frames[2][2][1])), 0.02)

    def test_second_root_moves_independently_and_quaternion_sign_is_stable(self):
        original = self.frames[1][2][2]
        final = self.frames[-2][2][2]
        self.assertAlmostEqual(final[0]-original[0], 1.0, delta=0.0005)
        self.assertAlmostEqual(final[1]-original[1], 0, delta=0.0005)
        self.assertAlmostEqual(final[2]-original[2], 0, delta=0.0005)

    def test_animation_moves_weighted_vertex_without_freezing(self):
        visited = [frame[2][3] for frame in self.frames[1:7]]
        self.assertGreater(
            len({tuple(round(v, 3) for v in xyz) for xyz in visited}), 4)
        # All positions are finite and bounded, never a torn or corrupt frame.
        for xyz in visited:
            self.assertTrue(all(math.isfinite(v) and abs(v) < 100 for v in xyz))

    def test_malformed_or_incomplete_native_timeline_is_rejected(self):
        failures = [
            self.native_stdout.replace("FRAME 0", "FRAME 8", 1),
            self.native_stdout.replace("END", "BAD", 1),
            self.native_stdout.replace("V ", "V nan ", 1),
            self.native_stdout.rsplit("FRAME 7", 1)[0],
            self.native_stdout.replace("M ", "M 1 ", 1),
        ]
        for bad in failures:
            with self.subTest(length=len(bad)):
                with self.assertRaises((ValueError, StopIteration)):
                    parse_frames(bad)


if __name__ == "__main__":
    unittest.main()
