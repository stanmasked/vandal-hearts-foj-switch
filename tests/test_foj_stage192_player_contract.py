"""Stage 192: verify production C pause/resume and crossfade against Python.

The reference independently samples synthetic clips, blends *local* XYZW
quaternions/XYZ and builds palettes with the Stage 190 geometric oracle.
No protected PS3 game data, authentic blend-graph assumptions or Switch.
"""
from __future__ import annotations

import math
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_foj_stage190_skin_matrix_contract import (
    IDENTITY, Q, bone, expected, vertex
)
from tests.test_foj_stage191_multiframe_skin_oracle import interpolated

ROOT = Path(__file__).resolve().parents[1]

# label, active_clip, old_clip_time, incoming_time, fade_alpha, paused
STEPS = (
    ("start", 0, 0, -1, 0, 0),
    ("run_025", 0, .25, -1, 0, 0),
    ("paused", 0, .25, -1, 0, 1),
    ("resumed", 0, .5, -1, 0, 0),
    ("fade_0", 0, .5, 0, 0, 0),
    ("fade_025", 0, .625, .125, .25, 0),
    ("fade_050", 0, .75, .25, .5, 0),
    ("fade_paused", 0, .75, .25, .5, 1),
    ("fade_075", 0, .875, .375, .75, 0),
    ("fade_end", 1, .5, -1, 0, 0),
    ("run_b075", 1, .75, -1, 0, 0),
    ("run_b1_clamped", 1, 1, -1, 0, 0),
    ("instant_a", 0, 0, -1, 0, 0),
)


def clips():
    a = (
        ((0, IDENTITY, (0, 0, 0)), (1, (0, 0, Q, Q), (1, 0, 0))),
        ((0, IDENTITY, (0, 2, 0)), (1, (0, 0, Q, Q), (0, 2, 0))),
    )
    b = (
        ((0, (0, 0, Q, Q), (1, 0, 0)),
         (1, (0, 0, -1, 0), (2, 0, 0))),
        ((0, (0, 0, Q, Q), (0, 2, 0)),
         (1, (0, 0, -1, 0), (0, 2, 0))),
    )
    return a, b


def sample(track, t):
    if t <= track[0][0]:
        return track[0][1:]
    if t >= track[-1][0]:
        return track[-1][1:]
    lo, hi = track
    a = (t-lo[0])/(hi[0]-lo[0])
    quat = interpolated(lo[1], hi[1], a)
    xyz = tuple((1-a)*x+a*y for x,y in zip(lo[2],hi[2],strict=True))
    return quat, xyz


def oracle(clip_id, time, incoming_time, blend):
    a,b = clips()
    bind = (bone(-1,0,0,0),bone(0,0,2,0))
    poses = [sample(track,time) for track in (a,b)[clip_id]]
    if incoming_time >= 0:
        target = [sample(track,incoming_time) for track in b]
        joined = []
        for (from_q,from_t),(to_q,to_t) in zip(poses,target,strict=True):
            quat=interpolated(from_q,to_q,blend)
            xyz=tuple((1-blend)*x+blend*y for x,y in
                      zip(from_t,to_t,strict=True))
            joined.append((quat,xyz))
        poses = joined
    animation = [(bind[i][0], q, pos)
                 for i,(q,pos) in enumerate(poses)]
    return expected(bind,animation,(
        vertex(1,2,0,(0,.25),(1,.75)),
    ))


def read_native(data):
    lines=iter(data.splitlines())
    records=[]
    for line in lines:
        if line=="GUARDS OK":
            if len(records)!=len(STEPS):
                raise ValueError("Missing native controller frame")
            if next(lines,None) is not None:
                raise ValueError("Trailing unverified native data")
            return records
        fields=line.split()
        if len(fields)!=7 or fields[0]!="STATE":
            raise ValueError("Unexpected native player record")
        label=fields[1]
        if len(records)>=len(STEPS) or label!=STEPS[len(records)][0]:
            raise ValueError("Duplicate, missing, or out-of-order state")
        try:
            metadata=(int(fields[2]),float(fields[3]),
                      float(fields[4]),float(fields[5]),int(fields[6]))
        except ValueError as exc:
            raise ValueError("Invalid state fields") from exc
        if not all(math.isfinite(x) for x in metadata):
            raise ValueError("Nonfinite native player time")
        for x,y in zip(metadata,STEPS[len(records)][1:],strict=True):
            if abs(x-y)>0.00001:
                raise ValueError("Incorrect active time, clip, alpha or pause")
        def next_vector(tag,n):
            row=next(lines,None)
            if row is None:
                raise ValueError("Truncated native trace")
            parts=row.split()
            if len(parts)!=n+1 or parts[0]!=tag:
                raise ValueError("Malformed native palette/vertex row")
            try:
                vec=tuple(float(v) for v in parts[1:])
            except ValueError as exc:
                raise ValueError("Non-numeric native coordinates") from exc
            if not all(math.isfinite(v) for v in vec):
                raise ValueError("Nonfinite native palette/vertex coordinate")
            return vec
        matrices=(next_vector("M",12),next_vector("M",12))
        point=next_vector("V",3)
        if next(lines,None)!="END":
            raise ValueError("Missing native state terminator")
        records.append((metadata,matrices,point))
    raise ValueError("Guard result missing from native probe")


class Stage192AnimationPlaybackContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.directory.cleanup)
        executable=str(Path(cls.directory.name)/"foj_stage192")
        build=subprocess.run(
            ["cc","-std=c11","-O2","-Wall","-Wextra","-Werror",
             "-pedantic","-Icore",
             "tools/foj_stage192_player_probe.c",
             "core/anim_player.c","core/skeletal_skin.c",
             "core/banim_core.c","-lm","-o",executable],
            cwd=ROOT,capture_output=True,text=True,timeout=30)
        if build.returncode!=0:
            raise AssertionError("Native player compilation failed: "+
                                 build.stderr[-1800:])
        run=subprocess.run([executable],cwd=ROOT,capture_output=True,
                           text=True,timeout=10)
        if run.returncode!=0:
            raise AssertionError("Native player guards failed: "+
                                 run.stderr[-1800:])
        cls.native=run.stdout
        cls.records=read_native(run.stdout)

    def assert_vector(self,seen,expect,tolerance=.0007):
        self.assertEqual(len(seen),len(expect))
        for component,(a,b) in enumerate(zip(seen,expect,strict=True)):
            self.assertAlmostEqual(a,b,delta=tolerance,msg=str(component))

    def test_every_state_matches_independent_python_pose_and_skinning(self):
        for step,(metadata,matrices,point) in zip(STEPS,self.records,strict=True):
            with self.subTest(state=step[0]):
                expected_matrices,expected_points=oracle(
                    step[1],step[2],step[3],step[4])
                for native,oracle_matrix in zip(matrices,expected_matrices,strict=True):
                    self.assert_vector(native,oracle_matrix)
                self.assert_vector(point,expected_points[0])

    def test_pause_and_fade_pause_are_exactly_stable(self):
        for before,during in ((1,2),(6,7)):
            self.assertEqual(self.records[before][1:],self.records[during][1:])

    def test_switch_at_alpha_zero_is_continuous(self):
        self.assertEqual(self.records[3][1:],self.records[4][1:])

    def test_fade_has_intermediate_stages_not_instant_snap(self):
        start=self.records[4][2]
        intermediate=[self.records[i][2] for i in (5,6,8)]
        end=self.records[9][2]
        self.assertTrue(all(start!=p and p!=end for p in intermediate))
        self.assertGreater(len(set(intermediate)),2)

    def test_no_unbounded_frame_to_frame_teleports(self):
        indices=(0,1,3,4,5,6,8,9,10,11)
        points=[self.records[i][2] for i in indices]
        shifts=[math.dist(a,b) for a,b in zip(points,points[1:])]
        self.assertLess(max(shifts),3.0)

    def test_invalid_inputs_do_not_mutate_player_or_output(self):
        self.assertIn("GUARDS OK",self.native)
        self.assertEqual(self.records[3][0][1],.5)
        self.assertEqual(self.records[9][0][0],1)

    def test_instant_switch_restarts_clip_a_at_time_zero(self):
        self.assert_vector(self.records[-1][2],self.records[0][2])
        self.assertEqual(self.records[-1][0][1],0)

    def test_corrupted_or_missing_native_trace_fails_closed(self):
        cases=(
            self.native.replace("GUARDS OK","FAKE",1),
            self.native.replace("STATE start","STATE bad",1),
            self.native.replace("M ","M nan ",1),
            self.native.replace("V ","V nan ",1),
            self.native.replace("STATE fade_end 1","STATE fade_end 0",1),
            self.native.rsplit("STATE instant_a",1)[0],
        )
        for bad in cases:
            with self.subTest(length=len(bad)):
                with self.assertRaises(ValueError):
                    read_native(bad)


if __name__=="__main__":
    unittest.main()
