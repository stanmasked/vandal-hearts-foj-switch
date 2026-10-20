"""Stage268 pure-geometry tests; fabricated surfaces, NOT GPU screenshots."""
from dataclasses import replace
from itertools import permutations
from math import inf, nan
import unittest

from tools.foj_stage268_transparency_crossing import (
    Triangle, UnsafeTransparencyOrder, MAX_TRIANGLES,
    example_crossing_pair, pair_relation, plan_back_to_front,
)

BASE_XY = ((-.70, -.45), (.70, -.45), (0., .70))


def triangle(name, z, xy=BASE_XY, reverse=False):
    depth_values = (z,z,z) if isinstance(z,(int,float)) else z
    v = tuple((x,y,d) for (x,y),d in zip(xy,depth_values))
    return Triangle(name, v[::-1] if reverse else v)


class CrossingGuardTests(unittest.TestCase):
    def test_stage267_safe_layers_are_farthest_first(self):
        back = triangle("cool", .20, ((-.35,-.50),(.75,-.50),(.20,.69)))
        middle = triangle("warm", .55, ((-.76,-.50),(.34,-.50),(-.21,.69)))
        near = triangle("violet", .85, ((-.76,-.50),(.34,-.50),(-.21,.69)))
        for ordering in permutations((near,back,middle)):
            self.assertEqual(plan_back_to_front(ordering),
                             ("cool","warm","violet"))

    def test_coplanar_overlapping_triangles_rejected(self):
        a=triangle("a", .5)
        b=triangle("b", .5)
        with self.assertRaises(UnsafeTransparencyOrder):
            pair_relation(a,b)

    def test_crossing_depth_order_rejected(self):
        a,b=example_crossing_pair()
        with self.assertRaisesRegex(UnsafeTransparencyOrder,"Depth crossing"):
            pair_relation(a,b)
        with self.assertRaises(UnsafeTransparencyOrder):
            plan_back_to_front((a,b))

    def test_opposite_orientation_does_not_hide_crossing(self):
        a,b=example_crossing_pair()
        for aa,bb in ((a,replace(b,vertices=b.vertices[::-1])),
                      (replace(a,vertices=a.vertices[::-1]),b),
                      (replace(a,vertices=a.vertices[::-1]),
                       replace(b,vertices=b.vertices[::-1]))):
            with self.subTest(aa=aa.vertices,bb=bb.vertices):
                with self.assertRaises(UnsafeTransparencyOrder):
                    pair_relation(aa,bb)

    def test_near_constant_depth_behind_far_and_reversal(self):
        left=triangle("left", .25)
        right=triangle("right", .75,reverse=True)
        self.assertEqual(pair_relation(left,right),"a_before_b")
        self.assertEqual(pair_relation(right,left),"b_before_a")
        self.assertEqual(plan_back_to_front([right,left]),("left","right"))

    def test_disjoint_interiors_and_touching_edges_do_not_require_order(self):
        left=triangle("left", .4, ((-.9,-.7),(-.4,-.7),(-.65,-.2)))
        right=triangle("right", .3, ((.4,-.7),(.9,-.7),(.65,-.2)))
        self.assertEqual(pair_relation(left,right),"disjoint")
        self.assertEqual(plan_back_to_front((right,left)),("left","right"))
        a=triangle("a", .5, ((0.,0.),(.4,0.),(0.,.4)))
        b=triangle("b", .4, ((.4,0.),(.8,0.),(.4,.4)))
        self.assertEqual(pair_relation(a,b),"disjoint")

    def test_partial_overlap_and_containment(self):
        a=triangle("rear", .2)
        b=triangle("near", .8, ((-.35,-.2),(.35,-.2),(0.,.4)))
        self.assertEqual(pair_relation(a,b),"a_before_b")
        self.assertEqual(plan_back_to_front((b,a)),("rear","near"))
        c=triangle("shift", .8, ((-.2,-.55),(.9,-.55),(.4,.58)))
        self.assertEqual(pair_relation(a,c),"a_before_b")

    def test_nearly_equal_overlapping_depth_rejected(self):
        a=triangle("a", .5)
        b=triangle("b", .5 + 0.2e-6)
        with self.assertRaises(UnsafeTransparencyOrder):
            pair_relation(a,b)

    def test_invalid_geometry_fails_closed(self):
        valid=triangle("valid", .5)
        malformed = [
            Triangle("",valid.vertices),
            Triangle("  ",valid.vertices),
            Triangle("bool", ((0.,0.,True),(.3,0.,.4),(0.,.3,.4))),
            Triangle("nan", ((0.,0.,nan),(.3,0.,.4),(0.,.3,.4))),
            Triangle("inf", ((0.,0.,inf),(.3,0.,.4),(0.,.3,.4))),
            Triangle("z", ((0.,0.,-1.),(.3,0.,.4),(0.,.3,.4))),
            Triangle("x", ((-1.01,0.,.3),(.3,0.,.4),(0.,.3,.4))),
            Triangle("flat", ((0.,0.,.1),(.3,0.,.2),(.6,0.,.3))),
            Triangle("two", valid.vertices[:2]),
            Triangle("list", list(valid.vertices)),
        ]
        for item in malformed:
            with self.subTest(name=item.name),self.assertRaises(ValueError):
                plan_back_to_front((item,))
        with self.assertRaises(ValueError):plan_back_to_front(())
        with self.assertRaises(ValueError):plan_back_to_front((valid,valid))
        with self.assertRaises(ValueError):pair_relation(valid,valid)

    def test_cardinality_limit(self):
        samples=tuple(triangle(f"t{i}",.5,((-.9,-.7),(-.4,-.7),(-.65,-.2)))
                      for i in range(MAX_TRIANGLES+1))
        with self.assertRaises(ValueError):
            plan_back_to_front(samples)

    def test_input_order_independence_on_disjoint_inputs(self):
        a=triangle("z",.4,((-.9,-.7),(-.4,-.7),(-.65,-.2)))
        b=triangle("a",.1,((.4,-.7),(.9,-.7),(.65,-.2)))
        self.assertEqual(plan_back_to_front((a,b)),("a","z"))
        self.assertEqual(plan_back_to_front((b,a)),("a","z"))


if __name__=="__main__":
    unittest.main()
