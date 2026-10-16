import unittest
from tools.gpu_triangle_reference import (
    WIDTH, HEIGHT, VERTICES, palette, project, reference_pixel, triangle_uv
)


class SyntheticGpuTriangleTests(unittest.TestCase):
    def test_exact_projection_and_winding(self):
        self.assertEqual(project(*VERTICES[0][:2]), (256.0, 558.0))
        self.assertEqual(project(*VERTICES[1][:2]), (1024.0, 558.0))
        self.assertAlmostEqual(project(*VERTICES[2][:2])[0], 640.0)
        self.assertAlmostEqual(project(*VERTICES[2][:2])[1], 126.0)
        self.assertEqual((WIDTH, HEIGHT), (1280, 720))

    def test_centroid_uv_matches_synthetic_shader(self):
        u, v = triangle_uv(640, 414)
        self.assertAlmostEqual(u, 0.5)
        self.assertAlmostEqual(v, 1 / 3)
        result = reference_pixel(640, 414)
        self.assertTrue(result["inside_triangle"])
        self.assertAlmostEqual(result["rgba_float"][0], 0.5, delta=.003)
        self.assertAlmostEqual(result["rgba_float"][1], 1/3, delta=.003)
        self.assertEqual(result["rgba_float"][2], 0.3)

    def test_background_and_palette_changes_only_on_outside(self):
        self.assertIsNone(triangle_uv(0, 0))
        self.assertEqual(palette(0), (.21, .12, .23, 1.0))
        self.assertAlmostEqual(palette(120)[0], .44)
        self.assertAlmostEqual(palette(120)[1], .57)
        self.assertEqual(palette(240), palette(0))
        p0 = reference_pixel(0, 0, 0)
        p1 = reference_pixel(0, 0, 120)
        self.assertNotEqual(p0["rgba_float"], p1["rgba_float"])
        self.assertEqual(reference_pixel(640, 414, 0)["rgba_float"],
                         reference_pixel(640, 414, 120)["rgba_float"])

    def test_outside_and_invalid_input(self):
        self.assertIsNone(triangle_uv(640, 701))
        self.assertIsNone(triangle_uv(1279, 719))
        for x, y in ((-1, 0), (1280, 0), (0, -1), (0, 720)):
            with self.assertRaises(ValueError):
                reference_pixel(x, y)
        for frame in (-1, 2**64):
            with self.assertRaises(ValueError):
                palette(frame)


if __name__ == "__main__":
    unittest.main()
