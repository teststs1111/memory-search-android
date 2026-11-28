import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGES = ROOT / "app" / "src" / "main" / "assets" / "stages"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Chapter8CandidateReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read_json(STAGES / "chapter_8_label_boxes.candidates.json")
        cls.runtime = read_json(STAGES / "chapter_8.json")
        catalog = read_json(STAGES / "item_catalogs.json")
        cls.names = next(
            chapter["itemNames"]
            for chapter in catalog["chapters"]
            if chapter["stageId"] == "chapter_8"
        )

    def test_candidate_schema_uses_highlight_label_box_purpose(self):
        self.assertEqual(self.candidates["purpose"], "highlight_item_name_label_box")

    def test_candidate_names_and_ids_match_catalog_order(self):
        items = self.candidates["items"]
        self.assertEqual([item["itemName"] for item in items], self.names)
        ids = [item["itemId"] for item in items]
        self.assertEqual(len(ids), len(self.names))
        self.assertEqual(len(set(ids)), len(ids))

    def test_reference_dimensions_and_coordinate_basis_are_valid(self):
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
        self.assertEqual(
            data["sourceImage"]["annotatedSha256"],
            "5a856136e315f72fb9a490f01e2543603968229af26e99ef8230b0d6c9f92043",
        )
        self.assertEqual(
            data["sourceImage"]["baseSha256"],
            "2aa5632837d273242d44637944615cfce88f653ed6ca402f7bea28910b7734c5",
        )

    def test_source_rectangles_match_normalized_bounds(self):
        basis = self.candidates["imageSize"]
        for item in self.candidates["items"]:
            rect = item.get("sourceRect")
            if rect is None:
                self.assertIsNone(item.get("bounds"), item["itemName"])
                continue
            x1, y1, x2, y2 = rect
            self.assertTrue(0 <= x1 < x2 <= basis["width"], item["itemName"])
            self.assertTrue(0 <= y1 < y2 <= basis["height"], item["itemName"])
            expected = {
                "left": x1 / basis["width"],
                "top": y1 / basis["height"],
                "right": x2 / basis["width"],
                "bottom": y2 / basis["height"],
            }
            for key, value in expected.items():
                self.assertAlmostEqual(
                    item["bounds"][key], value, places=6, msg=item["itemName"]
                )
            self.assertEqual(item["source"], "annotated")
            self.assertEqual(item["status"], "candidate_needs_visual_review")

    def test_edge_clipped_candidates_remain_pending(self):
        expected = {
            "星型クッション", "ゲーム機張り紙", "作業用手袋",
            "ドライバー", "レンチ", "ハンマー",
        }
        actual = {
            item["itemName"]
            for item in self.candidates["items"]
            if item.get("visualReviewStatus") == "edge_clipped_pending_full_bounds"
        }
        self.assertEqual(actual, expected)
        review = self.candidates["visualReview"]
        self.assertEqual(review["edgeClippedCandidateCount"], 6)
        self.assertEqual(set(review["edgeClippedItemNames"]), expected)
        self.assertEqual(review["visuallyGroundedCompleteCount"], 26)

    def test_catalog_reference_mismatch_is_explicit_and_not_guessed(self):
        items = {item["itemName"]: item for item in self.candidates["items"]}
        missing = items["ネジ"]
        self.assertIsNone(missing["sourceRect"])
        self.assertIsNone(missing["bounds"])
        self.assertEqual(
            missing["visualReviewStatus"], "catalog_item_not_found_in_reference"
        )
        self.assertEqual(
            self.candidates["visualReview"]["missingCatalogItemNames"], ["ネジ"]
        )
        self.assertEqual(
            self.candidates["visualReview"]["unmatchedAnnotatedLabels"], ["ポップコーン"]
        )

    def test_axis_aligned_overlaps_are_recorded_without_auto_correction(self):
        items = self.candidates["items"]
        expected = []
        for index, first in enumerate(items):
            a = first.get("bounds")
            if a is None:
                continue
            for second in items[index + 1:]:
                b = second.get("bounds")
                if b is None:
                    continue
                overlap_width = max(
                    0.0, min(a["right"], b["right"]) - max(a["left"], b["left"])
                )
                overlap_height = max(
                    0.0, min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
                )
                if overlap_width * overlap_height > 0:
                    expected.append([first["itemName"], second["itemName"]])
        self.assertEqual(
            self.candidates["visualReview"]["overlappingCandidatePairs"], expected
        )
        self.assertEqual(len(expected), 21)
        self.assertFalse(
            self.candidates["visualReview"]["detectorOutputUsedAsCoordinateSource"]
        )

    def test_chapter_eight_runtime_coordinates_remain_disabled(self):
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
