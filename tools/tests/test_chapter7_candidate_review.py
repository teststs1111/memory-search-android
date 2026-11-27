import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGES = ROOT / "app" / "src" / "main" / "assets" / "stages"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Chapter7CandidateReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read_json(STAGES / "chapter_7_label_boxes.candidates.json")
        cls.runtime = read_json(STAGES / "chapter_7.json")
        catalog = read_json(STAGES / "item_catalogs.json")
        cls.names = next(
            chapter["itemNames"]
            for chapter in catalog["chapters"]
            if chapter["stageId"] == "chapter_7"
        )

    def test_candidate_names_and_ids_match_catalog_order(self):
        items = self.candidates["items"]
        self.assertEqual([item["itemName"] for item in items], self.names)
        ids = [item["itemId"] for item in items]
        self.assertEqual(len(ids), 35)
        self.assertEqual(len(set(ids)), 35)

    def test_coordinate_basis_and_source_rectangles_are_valid(self):
        data = self.candidates
        self.assertEqual(data["imageSize"], {"width": 563, "height": 1000})
        self.assertEqual(
            data["actualReferenceImageSize"], {"width": 1206, "height": 2144}
        )
        actual = data["actualReferenceImageSize"]
        basis = data["imageSize"]
        self.assertLess(
            abs(actual["width"] / actual["height"] - basis["width"] / basis["height"]),
            0.001,
        )
        for item in data["items"]:
            x1, y1, x2, y2 = item["sourceRect"]
            self.assertTrue(0 <= x1 < x2 <= basis["width"], item["itemName"])
            self.assertTrue(0 <= y1 < y2 <= basis["height"], item["itemName"])
            bounds = item["bounds"]
            expected = {
                "left": x1 / basis["width"],
                "top": y1 / basis["height"],
                "right": x2 / basis["width"],
                "bottom": y2 / basis["height"],
            }
            for key, value in expected.items():
                self.assertAlmostEqual(bounds[key], value, places=6, msg=item["itemName"])
            self.assertEqual(item["source"], "annotated")
            self.assertNotEqual(item["status"], "verified")

    def test_edge_clipped_candidates_remain_pending(self):
        expected = {
            "ビーチボール", "壊れたロボット", "卓上カレンダー", "ハサミ",
            "ストップウォッチ", "メガネ", "ゴーグル", "ルービックキューブ",
            "救急箱", "ボールペン",
        }
        actual = {
            item["itemName"]
            for item in self.candidates["items"]
            if item.get("visualReviewStatus") == "edge_clipped_pending_full_bounds"
        }
        self.assertEqual(actual, expected)
        review = self.candidates["visualReview"]
        self.assertEqual(review["edgeClippedCandidateCount"], 10)
        self.assertEqual(set(review["edgeClippedItemNames"]), expected)
        self.assertEqual(review["visuallyGroundedCompleteCount"], 25)

    def test_axis_aligned_overlaps_are_recorded_without_auto_correction(self):
        items = self.candidates["items"]
        expected = []
        for index, first in enumerate(items):
            a = first["bounds"]
            for second in items[index + 1:]:
                b = second["bounds"]
                overlap_width = max(0.0, min(a["right"], b["right"]) - max(a["left"], b["left"]))
                overlap_height = max(0.0, min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]))
                if overlap_width * overlap_height > 0:
                    expected.append([first["itemName"], second["itemName"]])
        self.assertEqual(
            self.candidates["visualReview"]["overlappingCandidatePairs"], expected
        )
        self.assertEqual(len(expected), 26)
        self.assertFalse(self.candidates["visualReview"]["detectorOutputUsedAsCoordinateSource"])

    def test_chapter_seven_runtime_coordinates_remain_disabled(self):
        self.assertFalse(self.candidates["runtimeEnabled"])
        self.assertEqual(
            self.candidates["dataStatus"], "partially_reviewed_candidate_only"
        )
        self.assertEqual(
            self.runtime["dataStatus"], "awaiting_coordinate_verification"
        )
        self.assertEqual(self.runtime["items"], [])


if __name__ == "__main__":
    unittest.main()
