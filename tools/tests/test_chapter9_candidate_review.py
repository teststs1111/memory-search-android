import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGES = ROOT / "app" / "src" / "main" / "assets" / "stages"
sys.path.insert(0, str(ROOT / "tools"))

from render_chapter9_label_boxes import (  # noqa: E402
    ANNOTATED_IMAGE,
    BASE_IMAGE,
    compute_alignment,
    mapped_basis_rect,
    sha256,
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Chapter9CandidateReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = read_json(STAGES / "chapter_9_label_boxes.candidates.json")
        cls.runtime = read_json(STAGES / "chapter_9.json")
        cls.catalog = read_json(STAGES / "item_catalogs.json")
        cls.names = next(
            chapter["itemNames"]
            for chapter in cls.catalog["chapters"]
            if chapter["stageId"] == "chapter_9"
        )

    def test_candidate_names_and_ids_match_catalog_order(self):
        items = self.candidates["items"]
        self.assertEqual([item["itemName"] for item in items], self.names)
        ids = [item["itemId"] for item in items]
        self.assertEqual(len(ids), len(self.names))
        self.assertEqual(len(set(ids)), len(ids))

    def test_reference_dimensions_and_hashes_are_exact(self):
        data = self.candidates
        self.assertEqual(data["imageSize"], {"width": 563, "height": 1000})
        self.assertEqual(
            data["actualReferenceImageSize"], {"width": 1404, "height": 2496}
        )
        self.assertEqual(
            data["actualAnnotatedImageSize"], {"width": 1992, "height": 2490}
        )
        self.assertEqual(
            sha256(ANNOTATED_IMAGE), data["sourceImage"]["annotatedSha256"]
        )
        self.assertEqual(sha256(BASE_IMAGE), data["sourceImage"]["baseSha256"])

    def test_source_rectangles_match_normalized_bounds(self):
        basis = self.candidates["imageSize"]
        for item in self.candidates["items"]:
            rect = item.get("sourceRect")
            if rect is None:
                self.assertIsNone(item.get("bounds"), item["itemName"])
                self.assertIsNone(item.get("annotatedSourceRect"), item["itemName"])
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

    def test_edge_and_near_edge_candidates_remain_pending(self):
        review = self.candidates["visualReview"]
        edge_expected = {"クッション", "プリン", "作業用手袋"}
        near_expected = {"ヘッドホン", "タブレット"}
        edge_actual = {
            item["itemName"] for item in self.candidates["items"]
            if item.get("visualReviewStatus") == "edge_clipped_pending_full_bounds"
        }
        near_actual = {
            item["itemName"] for item in self.candidates["items"]
            if item.get("visualReviewStatus") == "near_edge_alignment_pending"
        }
        self.assertEqual(edge_actual, edge_expected)
        self.assertEqual(near_actual, near_expected)
        self.assertEqual(review["edgeClippedCandidateCount"], 3)
        self.assertEqual(review["nearEdgeCandidateCount"], 2)
        self.assertEqual(review["visuallyGroundedCompleteCount"], 28)

    def test_catalog_and_annotation_mismatches_are_explicit(self):
        items = {item["itemName"]: item for item in self.candidates["items"]}
        missing = items["ランチ"]
        self.assertIsNone(missing["sourceRect"])
        self.assertIsNone(missing["bounds"])
        self.assertEqual(missing["visualReviewStatus"], "missing_annotated_label")
        review = self.candidates["visualReview"]
        self.assertEqual(review["missingCatalogItemNames"], ["ランチ"])
        self.assertEqual(
            {item["itemName"] for item in review["unmatchedAnnotatedLabels"]},
            {"救急箱", "ハサミ"},
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
        self.assertEqual(len(expected), 11)
        self.assertFalse(
            self.candidates["visualReview"]["detectorOutputUsedAsCoordinateSource"]
        )

    def test_annotation_to_clean_alignment_reproduces_candidate_rectangles(self):
        import cv2

        annotated = cv2.imread(str(ANNOTATED_IMAGE), cv2.IMREAD_COLOR)
        base = cv2.imread(str(BASE_IMAGE), cv2.IMREAD_COLOR)
        matrix, good, inliers, ratio = compute_alignment(annotated, base)
        expected = self.candidates["referenceImageAlignment"]["annotatedToBaseHomography"]
        self.assertLess(
            max(abs(matrix[i, j] - expected[i][j]) for i in range(3) for j in range(3)),
            0.005,
        )
        self.assertGreaterEqual(good, 1000)
        self.assertGreaterEqual(inliers, 1000)
        self.assertGreater(ratio, 0.90)
        for item in self.candidates["items"]:
            if item.get("annotatedSourceRect") is None:
                continue
            mapped = mapped_basis_rect(
                item["annotatedSourceRect"], matrix, base.shape, self.candidates["imageSize"]
            )
            visible = item["sourceRect"]
            self.assertLessEqual(
                max(abs(mapped[i] - visible[i]) for i in range(4)), 4.0,
                item["itemName"],
            )

    def test_runtime_coordinates_remain_disabled(self):
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
