"""Synthetic-only Stage266 draw ordering; no assertion of real GPU output."""
from dataclasses import replace
import math
import unittest

from tools.foj_stage266_transparency_order import (
    COOL, WARM, VIOLET, Layer, order_layers, composite_rgb, example_three_layers,
)


class TransparencyOrderTests(unittest.TestCase):
    def test_stage265_single_layer_reference_preserved(self):
        rear = Layer("rear", .20, (*COOL, 255), "opaque_rear")
        for alpha, expected in [(0, COOL), (128, (127,128,123)), (255,WARM)]:
            with self.subTest(alpha=alpha):
                near = Layer("front", .55, (*WARM, alpha), "translucent_front")
                self.assertEqual(composite_rgb(order_layers([near, rear])), expected)

    def test_two_translucent_layers_sorted_far_to_near(self):
        steps = order_layers(example_three_layers())
        self.assertEqual([s.name for s in steps], ["rear-cool", "middle-warm", "near-violet"])
        self.assertEqual([s.depth_write_enabled for s in steps], [True,False,False])
        self.assertEqual([s.blending_enabled for s in steps], [False,True,True])
        self.assertTrue(all(s.depth_test_enabled for s in steps))
        self.assertEqual(composite_rgb(steps), (111,100,162))

    def test_wrong_order_yields_different_rgb_and_is_rejected(self):
        steps = order_layers(example_three_layers())
        with self.assertRaisesRegex(ValueError, "back-to-front"):
            composite_rgb((steps[0],steps[2],steps[1]))
        # Reverse compositing even when both alpha values are 128 is different.
        def mix(f,b): return tuple(round((128*f[i] + 127*b[i])/255) for i in range(3))
        self.assertNotEqual(mix(WARM,mix(VIOLET,COOL)), composite_rgb(steps))

    def test_zero_alpha_is_noop_and_full_alpha_overwrites(self):
        layers = list(example_three_layers())
        layers[0] = replace(layers[0], rgba=(*VIOLET,0))
        self.assertEqual(composite_rgb(order_layers(layers)), (127,128,123))
        layers[0] = replace(layers[0], rgba=(*VIOLET,255))
        self.assertEqual(composite_rgb(order_layers(layers)), VIOLET)

    def test_bad_depth_flags_or_blending_fail_closed(self):
        steps = order_layers(example_three_layers())
        for corrupted in (
            (replace(steps[0],depth_write_enabled=False),*steps[1:]),
            (steps[0],replace(steps[1],depth_write_enabled=True),steps[2]),
            (steps[0],replace(steps[1],blending_enabled=False),steps[2]),
            (steps[0],replace(steps[1],depth_test_enabled=False),steps[2]),
        ):
            with self.subTest(corrupted=corrupted), self.assertRaises(ValueError):
                composite_rgb(corrupted)

    def test_invalid_inputs_rejected(self):
        base = list(example_three_layers())
        invalid = [
            [base[1]],
            [base[1], base[1]],
            [base[0],base[2]],
            [replace(base[1],rgba=(*COOL,254)), base[0]],
            [replace(base[0],depth=math.nan),base[1]],
            [replace(base[0],depth=math.inf),base[1]],
            [replace(base[0],depth=.2),base[1]],
            [replace(base[0],depth=-.1),base[1]],
            [replace(base[0],rgba=(256,72,201,128)),base[1]],
            [replace(base[0],rgba=(True,72,201,128)),base[1]],
            [replace(base[0],kind="unknown"),base[1]],
            [replace(base[0],name=base[1].name),base[1]],
            [base[1],base[0],base[2],base[0]],
        ]
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                order_layers(bad)

    def test_submission_order_does_not_affect_plan(self):
        layers=example_three_layers()
        a=order_layers(layers)
        b=order_layers(tuple(reversed(layers)))
        self.assertEqual(a,b)
        self.assertEqual(composite_rgb(a),composite_rgb(b))
        self.assertEqual([l.name for l in layers], ["near-violet","rear-cool","middle-warm"])


if __name__ == "__main__":
    unittest.main()
