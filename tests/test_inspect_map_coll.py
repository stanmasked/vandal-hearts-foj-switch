"""Use invented map text; do not commit any of the user's game resources."""
import unittest
from tools.inspect_map_coll import (
    MapFormatError, summarize_collision, summarize_visibility,
    summarize_placement, validate_map_name,
)


def example_coll():
    return (b"2,2,-10.0,-10.0,10.0,10.0,\r\n"
            b"0,0,0,0,0,0,false,false,\r\n"
            b"1,0,1,1,1,1,true,false,\r\n"
            b"0,1,0,1,2,3,false,true,\r\n"
            b"1,1,2,2,2,2,false,false,\r\n")


class GameMapSummaryTests(unittest.TestCase):
    def test_collision_grid(self):
        r = summarize_collision(example_coll())
        self.assertEqual((r["width"], r["height"]), (2, 2))
        self.assertEqual(r["cells"], 4)
        self.assertEqual(r["grid_origin"], [-10.0, -10.0])
        self.assertEqual(r["grid_step"], [10.0, 10.0])
        self.assertEqual(r["cells_with_nonzero_samples"], 3)
        self.assertEqual(r["cells_with_varied_samples"], 1)
        self.assertEqual(r["flag_true_counts"], [1, 1])
        self.assertEqual(r["sample_min"], 0)
        self.assertEqual(r["sample_max"], 3)

    def test_out_of_order_cell_rejected(self):
        raw = example_coll().replace(b"1,0,1,1,1,1,", b"2,0,1,1,1,1,")
        with self.assertRaisesRegex(MapFormatError, "row-major"):
            summarize_collision(raw)

    def test_wrong_collision_count_rejected(self):
        raw = example_coll().rsplit(b"\r\n", 2)[0] + b"\r\n"
        with self.assertRaisesRegex(MapFormatError, "row count"):
            summarize_collision(raw)

    def test_nonfinite_and_invalid_bool_rejected(self):
        with self.assertRaisesRegex(MapFormatError, "Non-finite"):
            summarize_collision(example_coll().replace(b"1,1,1,1,", b"nan,1,1,1,"))
        with self.assertRaisesRegex(MapFormatError, "boolean"):
            summarize_collision(example_coll().replace(b"true,false", b"yes,false"))

    def test_visibility_metadata(self):
        raw = (b"0\n2\n4\n"
               b"0,0,false,true\n1,0,false,true\n"
               b"0,1,false,true,extra\n1,1,false,true,extra\n")
        r = summarize_visibility(raw)
        self.assertEqual(r["records"], 4)
        self.assertEqual(r["column_count_histogram"], {4: 2, 5: 2})

    def test_visibility_bad_count(self):
        with self.assertRaisesRegex(MapFormatError, "row count"):
            summarize_visibility(b"0\n2\n5\n0,0,false\n")

    def test_placements_count_only(self):
        r = summarize_placement(
            b"[tree0]\nbase = tree\nlocation = 1,2,3\n"
            b"[tree1]\nbase = tree\nlocation = 3,2,1\n"
        )
        self.assertEqual(r["section_count"], 2)
        self.assertEqual(r["placement_property_keys"]["base"], 2)
        self.assertEqual(r["placement_property_keys"]["location"], 2)
        self.assertNotIn("1,2,3", str(r))

    def test_map_identifier_safety(self):
        self.assertEqual(validate_map_name("map1-1"), "map1-1")
        for value in ("../secrets", "a/b", "map 1", "", "foo\\bar"):
            with self.assertRaises(MapFormatError):
                validate_map_name(value)


if __name__ == "__main__":
    unittest.main()
