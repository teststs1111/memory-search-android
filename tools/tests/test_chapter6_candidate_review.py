import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGES = ROOT / "app" / "src" / "main" / "assets" / "stages"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Chapter6CandidateReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read_json(STAGES / "chapter_6_label_boxes.candidates.json")
        cls.stage = read_json(STAGES / "chapter_6.json")
        cls.catalog = read_json(STAGES / "item_catalogs.json")
        cls.chapter_names = next(
            chapter["itemNames"]
            for chapter in cls.catalog["chapters"]
            if chapter["stageId"] == "chapter_6"
        )

    def test_candidate_names_match_chapter_catalog_in_order(self):
        self.assertEqual(
            [item["itemName"] for item in self.candidates["items"]],
            self.chapter_names,
        )

    def test_source_rectangles_match_normalized_bounds(self):
        width = self.candidates["imageSize"]["width"]
        height = self.candidates["imageSize"]["height"]
        for item in self.candidates["items"]:
            x1, y1, x2, y2 = item["sourceRect"]
            expected = {
                "left": x1 / width,
                "top": y1 / height,
                "right": x2 / width,
                "bottom": y2 / height,
            }
            for key, value in expected.items():
                self.assertAlmostEqual(item["bounds"][key], value, places=6, msg=item["itemName"])

    def test_edge_clipped_boxes_remain_explicitly_pending(self):
        expected = {"バードフィーダー", "ハンカチ", "スクールバッグ", "鉢植え", "ラケット"}
        review = self.candidates["visualReview"]
        actual = {
            item["itemName"]
            for item in self.candidates["items"]
            if item.get("visualReviewStatus") == "edge_clipped_pending_full_bounds"
        }
        self.assertEqual(actual, expected)
        self.assertEqual(set(review["edgeClippedItemNames"]), expected)
        self.assertEqual(review["edgeClippedCandidateCount"], 5)
        self.assertEqual(review["actualReferenceImageSize"], {"width": 1404, "height": 2496})

    def test_red_water_bottle_label_is_visually_grounded_and_detector_is_not_coordinate_source(self):
        water_bottle = next(
            item for item in self.candidates["items"] if item["itemName"] == "水筒"
        )
        self.assertEqual(water_bottle["visualReviewStatus"], "visually_grounded_manual_red_label")
        detector = self.candidates["visualReview"]["automatedDetector"]
        self.assertEqual(detector["detectedCandidateCount"], 32)
        self.assertEqual(detector["unmatchedItemNames"], [])
        self.assertFalse(detector["usedAsCoordinateSource"])

    def test_overlapping_boxes_are_recorded_without_auto_correction(self):
        self.assertEqual(len(self.candidates["visualReview"]["overlappingCandidatePairs"]), 14)
        self.assertEqual(
            self.candidates["visualReview"]["status"],
            "partially_reviewed_candidate_only",
        )

    def test_chapter_six_runtime_coordinates_remain_disabled(self):
        self.assertFalse(self.candidates["runtimeEnabled"])
        self.assertEqual(self.stage["dataStatus"], "awaiting_coordinate_verification")
        self.assertEqual(self.stage["items"], [])


if __name__ == "__main__":
    unittest.main()
