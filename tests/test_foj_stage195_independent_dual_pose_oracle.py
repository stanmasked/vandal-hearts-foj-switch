"""Stage 195: compare actual C actor-session/fade matrices and skinned XYZ
with an independent Python quaternion-geometry oracle.

All tracks, model bones, vertices and weights are invented. This checks the
chosen research convention, not correctness against original PS3 animation.
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
from tests.test_foj_stage191_multiframe_skin_oracle import (
    key, sample_track, interpolated
)

ROOT = Path(__file__).resolve().parents[1]
NAMES = (
    "bind", "start", "play025", "pause025", "resume050",
    "fade0", "fade025", "fade050", "pause050", "fade075",
    "fade100", "b075", "b_end", "instant_a", "reset"
)
# state, active clip, active clock, next clock, fade alpha, paused
STATES = (
    ("bind", "A", 0., -1., 0., 1),
    ("start", "A", 0., -1., 0., 1),
    ("play025", "A", .25, -1., 0., 0),
    ("pause025", "A", .25, -1., 0., 1),
    ("resume050", "A", .5, -1., 0., 0),
    ("fade0", "A", .5, 0., 0., 1),
    ("fade025", "A", .625, .125, .25, 1),
    ("fade050", "A", .75, .25, .5, 1),
    ("pause050", "A", .75, .25, .5, 1),
    ("fade075", "A", .875, .375, .75, 0),
    ("fade100", "B", .5, -1., 0., 0),
    ("b075", "B", .75, -1., 0., 0),
    ("b_end", "B", 1., -1., 0., 0),
    ("instant_a", "A", 0., -1., 0., 0),
    ("reset", "A", 0., -1., 0., 1),
)


def fixture():
    bind = [
        bone(-1, 2, 1, 0),
        bone(0, 0, 2, 0),
        bone(-1, -4, 0, 1),
    ]
    a = [
        [key(0, IDENTITY, (2, 1, 0)),
         key(.5, (0, 0, Q, Q), (3, 1, 0)),
         key(1, (0, 0, 1, 0), (4, 1, 0))],
        [key(-.1, IDENTITY, (0, 2, 0)),
         key(.8, (Q, 0, 0, Q), (0, 3, 0))],
        [key(0, IDENTITY, (-4, 0, 1)),
         key(1, (0, 0, 0, -1), (-3, 0, 1))],
    ]
    b = [
        [key(0, (0, 0, -Q, Q), (1, 1, 0)),
         key(1, (0, 0, -1, 0), (0, 1, 0))],
        [key(0, (0, Q, 0, Q), (0, 2, 0)),
         key(1, (Q, 0, 0, Q), (0, 2, 1))],
        [key(0, (0, 0, Q, Q), (-4, 1, 1)),
         key(1, IDENTITY, (-2, 0, 1))],
    ]
    vertices = [
        vertex(3, 1, 0, (0, 1)),
        vertex(3, 3, 0, (1, 1)),
        vertex(-4, 0, 1, (2, 1)),
        vertex(4, 3, 0, (0, .25), (1, .75)),
        vertex(-2, 1, 1, (1, .4), (2, .6)),
        vertex(0, 0, 0),
    ]
    return bind, a, b, vertices


def predict(name, active, current_time, incoming_time, alpha):
    bind, a, b, vertices = fixture()
    if name == "bind":
        return expected(bind, bind, vertices)
    tracks = a if active == "A" else b
    sampled = [sample_track(track, current_time) for track in tracks]
    if incoming_time >= 0:
        dest = [sample_track(track, incoming_time) for track in b]
        blended = []
        for (from_q, from_xyz), (to_q, to_xyz) in zip(
            sampled, dest, strict=True
        ):
            if alpha == 0:
                rotation = from_q
            elif alpha == 1:
                rotation = to_q
            else:
                rotation = interpolated(from_q, to_q, alpha)
            location = tuple((1-alpha)*x + alpha*y for x, y in zip(
                from_xyz, to_xyz, strict=True
            ))
            blended.append((rotation, location))
        sampled = blended
    anim_bones = [
        (bind[i][0], sampled[i][0], sampled[i][1])
        for i in range(len(bind))
    ]
    return expected(bind, anim_bones, vertices)


def parse_trace(stdout: str):
    lines = iter(stdout.splitlines())
    frames = {}
    for state in STATES:
        values = next(lines).split()
        if len(values) != 7 or values[0] != "STATE":
            raise ValueError("Invalid native C state header")
        _, label, clip, clock, incoming, weight, paused = values
        if label != state[0] or clip != state[1]:
            raise ValueError("Wrong/reordered dual-clip state")
        if paused not in ("0", "1") or int(paused) != state[5]:
            raise ValueError("Wrong pause state")
        fields = [float(clock), float(incoming), float(weight)]
        if not all(math.isfinite(v) for v in fields):
            raise ValueError("Nonfinite player clock")
        if any(abs(a-b) > 1e-6 for a, b in zip(fields,state[2:5])):
            raise ValueError("Wrong fade clock or blend weight")
        def sample(marker, count):
            line = next(lines).split()
            if len(line) != count+1 or line[0] != marker:
                raise ValueError("Invalid matrix/vertex native C record")
            items = tuple(float(x) for x in line[1:])
            if not all(math.isfinite(x) for x in items):
                raise ValueError("Nonfinite native transform")
            return items
        matrices = tuple(sample("M",12) for _ in range(3))
        vertices = tuple(sample("V",3) for _ in range(6))
        if next(lines) != "END":
            raise ValueError("Missing trace state terminator")
        frames[label] = matrices, vertices
    if next(lines) != "GUARDS OK":
        raise ValueError("Native guard checks missing")
    try:
        next(lines)
    except StopIteration:
        return frames
    raise ValueError("Unrecognized native trace trailer")


class Stage195IndependentDualPoseOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        executable = str(Path(cls.tmp.name) / "foj_stage195_native_trace")
        subprocess.run(
            ["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
             "-pedantic", "-Icore", "tools/foj_stage195_dual_pose_probe.c",
             "core/rigged_actor_session.c", "core/anim_player.c",
             "core/rigmesh_io.c", "core/banim_core.c",
             "core/skeletal_skin.c", "-lm", "-o", executable],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
        )
        process = subprocess.run(
            [executable], cwd=ROOT, capture_output=True, text=True,
            check=True, timeout=12,
        )
        cls.stdout = process.stdout
        cls.frames = parse_trace(process.stdout)

    def assert_numeric(self, actual, expected_values, tolerance=.001):
        self.assertEqual(len(actual),len(expected_values))
        for i, (found, reference) in enumerate(zip(
            actual, expected_values, strict=True
        )):
            self.assertEqual(len(found),len(reference))
            for j,(got,want) in enumerate(zip(
                found,reference,strict=True
            )):
                self.assertAlmostEqual(
                    got,want,delta=tolerance,
                    msg=f"Row {i} component {j}: C vs independent Python"
                )

    def test_all_fifteen_states_match_independent_skin_matrices(self):
        self.assertEqual(set(self.frames),set(NAMES))
        for name,active,t,inc,alpha,_paused in STATES:
            with self.subTest(state=name):
                matrices, _ = self.frames[name]
                oracle_m, _ = predict(name,active,t,inc,alpha)
                self.assert_numeric(matrices,oracle_m)

    def test_all_fifteen_states_match_independent_weighted_vertices(self):
        for name,active,t,inc,alpha,_paused in STATES:
            with self.subTest(state=name):
                _, vertices = self.frames[name]
                _, oracle_vertices = predict(name,active,t,inc,alpha)
                self.assert_numeric(vertices,oracle_vertices)

    def test_bind_identity_exact_including_second_root(self):
        matrices, positions=self.frames["bind"]
        identity=(1,0,0,0,0,1,0,0,0,0,1,0)
        self.assert_numeric(matrices,[identity]*3)
        _,_,_,reference_vertices=fixture()
        self.assert_numeric(positions,[v[0] for v in reference_vertices])

    def test_pause_preserves_every_matrix_and_vertex(self):
        self.assertEqual(self.frames["play025"],self.frames["pause025"])
        self.assertEqual(self.frames["fade050"],self.frames["pause050"])

    def test_zero_alpha_does_not_move_vertices_or_matrices(self):
        self.assertEqual(self.frames["resume050"],self.frames["fade0"])

    def test_fade_moves_multiroot_and_blended_verts(self):
        def delta(a,b):
            first=self.frames[a][1]
            second=self.frames[b][1]
            return sum(abs(x-y) for p,q in zip(first,second)
                       for x,y in zip(p,q))
        for a,b in (
            ("fade0","fade025"),("fade025","fade050"),
            ("fade050","fade075"),("fade075","fade100"),
        ):
            self.assertGreater(delta(a,b),.03)
        self.assertEqual(self.frames["start"],self.frames["reset"])

    def test_unweighted_vertex_stays_fixed_everywhere(self):
        for _name,(_matrices,vertices) in self.frames.items():
            self.assert_numeric((vertices[-1],),((0.,0.,0.),))

    def test_clamp_and_immediate_switch(self):
        self.assertNotEqual(self.frames["b075"],self.frames["b_end"])
        self.assertEqual(self.frames["start"],self.frames["instant_a"])

    def test_reject_corrupted_missing_or_nonfinite_trace(self):
        bad=[
            self.stdout.replace("STATE start","STATE FAKE",1),
            self.stdout.replace("STATE fade050 A","STATE fade050 B",1),
            self.stdout.replace("M ","M nan ",1),
            self.stdout.replace("V ","V inf ",1),
            self.stdout.replace("GUARDS OK","GUARDS FAILED",1),
            self.stdout.rsplit("STATE reset",1)[0],
            self.stdout + "EXTRA\n",
            self.stdout.replace("fade050 A 0.75","fade050 A 0.25",1),
        ]
        for mutated in bad:
            with self.subTest(case=len(mutated)):
                with self.assertRaises((ValueError,StopIteration)):
                    parse_trace(mutated)


if __name__ == "__main__":
    unittest.main()
