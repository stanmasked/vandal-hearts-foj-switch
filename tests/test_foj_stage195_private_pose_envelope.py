"""Private pose-envelope numerical diagnostics on invented FoJ records only."""
from __future__ import annotations

import contextlib
from io import StringIO
import math
from pathlib import Path
import struct
import tempfile
import unittest

from tests.test_decode_rig_banim import synthetic_banim, synthetic_rig
from tests.test_inspect_complete_bmodel import synthetic_complete_model
from tools.export_local_rigmesh import pack_rig_mesh
from tools.foj_stage195_pose_geometry import predict_vertices
from tools.foj_stage195_private_pose_envelope import (
    SCHEMA, inspect_pose_envelope, main, metrics
)


class Stage195PrivatePoseEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        model=synthetic_complete_model()[:-4]+synthetic_rig()
        cls.rig,_=pack_rig_mesh(model)
        cls.clip=synthetic_banim()
        second=bytearray(cls.clip)
        struct.pack_into("<f",second,11+5+1+4+16,.25)
        cls.second=bytes(second)

    def test_private_single_clip_bind_is_identity(self):
        report=inspect_pose_envelope(self.rig,self.clip)
        self.assertEqual(report["schema"],SCHEMA)
        self.assertLessEqual(report["bind_identity_vertex_max"],.001)
        self.assertEqual(len(report["primary_pose_samples"]),3)
        self.assertIsNone(report["secondary_pose_samples"])
        self.assertFalse(report["original_ps3_skinning_math_verified"])

    def test_private_dual_clip_has_six_finite_aggregate_samples(self):
        report=inspect_pose_envelope(self.rig,self.clip,self.second)
        self.assertEqual(len(report["primary_pose_samples"]),3)
        self.assertEqual(len(report["secondary_pose_samples"]),3)
        for item in report["primary_pose_samples"]+report["secondary_pose_samples"]:
            self.assertIn(item["sample"],("start","midpoint","end"))
            self.assertTrue(math.isfinite(item["rms_source_vertex_displacement"]))
            self.assertGreaterEqual(item["max_source_vertex_displacement"],0)

    def test_payload_avoids_original_pose_arrays_paths_or_hashes(self):
        report=inspect_pose_envelope(self.rig,self.clip,self.second)
        as_text=str(report)
        for forbidden in ("rotation_xyzw","translation_xyz","filepath",
                          "sha256","local-data/","confidential.banim",
                          "original_geometry"):
            self.assertNotIn(forbidden,as_text)

    def test_rejects_duplicate_and_incompatible_second_clip(self):
        with self.assertRaisesRegex(ValueError,"distinct"):
            inspect_pose_envelope(self.rig,self.clip,self.clip)
        broken=bytearray(self.second)
        struct.pack_into("<H",broken,11+5+2*33+1,0xffff)
        with self.assertRaises(ValueError):
            inspect_pose_envelope(self.rig,self.clip,bytes(broken))

    def test_rejects_corrupt_source_rig_and_clip(self):
        for broken_rig,broken_clip in (
            (self.rig[:-1],self.clip),
            (self.rig,b"invalid"),
            (self.rig[:-1],self.clip[:-1]),
        ):
            with self.assertRaises(ValueError):
                inspect_pose_envelope(broken_rig,broken_clip)

    def test_independent_quaternion_oracle_bind_identity_multiroot(self):
        identity=(0.,0.,0.,1.)
        bind=[
            (-1,identity,(4.,1.,0.)),
            (0,identity,(0.,2.,0.)),
            (-1,identity,(-5.,0.,1.)),
        ]
        vertices=[
            ((5.,3.,0.),((1,1.),)),
            ((-4.,0.,1.),((2,1.),)),
            ((3.,2.,0.),((0,.4),(1,.6))),
            ((0.,0.,1.),()),
        ]
        result=predict_vertices(bind,bind,vertices)
        for got,entry in zip(result,vertices):
            for a,b in zip(got,entry[0]):
                self.assertAlmostEqual(a,b,delta=1e-8)

    def test_quaternion_oracle_detects_parent_rotation(self):
        identity=(0.,0.,0.,1.)
        q=math.sqrt(.5)
        bind=[(-1,identity,(2.,1.,0.)),(0,identity,(0.,2.,0.))]
        animation=[(-1,(0.,0.,q,q),(2.,1.,0.)),bind[1]]
        vertices=[((3.,3.,0.),((1,1.),))]
        posed=predict_vertices(bind,animation,vertices)
        self.assertAlmostEqual(posed[0][0],0,delta=.00001)
        self.assertAlmostEqual(posed[0][1],2,delta=.00001)

    def test_invalid_metrics_and_malformed_influence_fail_closed(self):
        with self.assertRaises(ValueError):
            metrics([(0,0,0)],[(float("nan"),0,0)])
        with self.assertRaises(ValueError):
            predict_vertices(
                [(-1,(0,0,0,1),(0,0,0))],
                [(-1,(0,0,0,1),(0,0,0))],
                [((1,2,3),((99,1.),))],
            )

    def test_private_cli_success_and_error_hide_all_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            rig=folder/"private_model.fojrm"
            a=folder/"private_animation_a.banim"
            b=folder/"private_animation_b.banim"
            rig.write_bytes(self.rig);a.write_bytes(self.clip)
            b.write_bytes(self.second)
            output=StringIO()
            with contextlib.redirect_stdout(output):
                result=main([str(rig),str(a),"--secondary",str(b)])
            self.assertEqual(result,0)
            self.assertNotIn(temp,output.getvalue())
            self.assertNotIn("private_animation",output.getvalue())
            b.write_bytes(b"bad data")
            error=StringIO()
            with contextlib.redirect_stderr(error):
                result=main([str(rig),str(a),"--secondary",str(b)])
            self.assertEqual(result,2)
            self.assertNotIn(temp,error.getvalue())
            self.assertNotIn(str(b),error.getvalue())


if __name__=="__main__":
    unittest.main()
