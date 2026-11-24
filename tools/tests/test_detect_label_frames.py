import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np

from detect_label_frames import align_annotated_to_base, detect_label_quadrilaterals, detect_seeded_label_quadrilaterals, make_annotation_difference_mask


class DetectLabelFramesTest(unittest.TestCase):
    # The detector must preserve rotated corners and ignore thin markup strokes.
    def test_resizes_same_aspect_annotated_image_to_base(self):
        annotated = np.zeros((200, 100, 3), dtype=np.uint8)
        base = np.zeros((100, 50, 3), dtype=np.uint8)
        aligned = align_annotated_to_base(annotated, base)
        self.assertEqual(aligned.shape, base.shape)

    def test_local_seed_detection_finds_rotated_label(self):
        base = np.full((500, 500, 3), (180, 180, 180), dtype=np.uint8)
        annotated = base.copy()
        rotated = cv2.boxPoints(((175, 130), (150, 48), 17)).astype(np.int32)
        cv2.fillConvexPoly(annotated, rotated, (190, 80, 210))
        items = [{"sourceRect": [100, 100, 250, 160]}]
        found = detect_seeded_label_quadrilaterals(annotated, items, {"width": 500, "height": 500}, 500, 500)
        self.assertIsNotNone(found[0])
        self.assertEqual(len(found[0]["points"]), 4)

    def test_difference_mask_follows_translucent_purple_fill_over_varied_background(self):
        height, width = 300, 300
        base = np.zeros((height, width, 3), dtype=np.uint8)
        # Use a textured, colorful scene so the overlay's final HSV color is
        # not constant across the label backing.
        for y in range(height):
            for x in range(width):
                base[y, x] = ((x * 3) % 255, (y * 2) % 255, (x + y) % 255)

        annotated = base.copy()
        roi = annotated[90:155, 70:245].astype(np.float32)
        purple = np.array([190, 80, 210], dtype=np.float32)
        annotated[90:155, 70:245] = np.clip(roi * 0.58 + purple * 0.42, 0, 255).astype(np.uint8)

        mask = make_annotation_difference_mask(annotated, base)
        self.assertGreater(cv2.countNonZero(mask[90:155, 70:245]), 9000)
        self.assertLess(cv2.countNonZero(mask[:70, :]), 20)

        items = [{"sourceRect": [70, 90, 245, 155]}]
        found = detect_seeded_label_quadrilaterals(
            annotated, items, {"width": width, "height": height},
            width, height, base=base
        )
        self.assertIsNotNone(found[0])
        self.assertAlmostEqual(found[0]["center"][0], 157.5, delta=3)
        self.assertAlmostEqual(found[0]["center"][1], 122.5, delta=3)

    def test_seeded_detector_splits_two_touching_label_fills(self):
        base = np.full((300, 500, 3), (130, 140, 150), dtype=np.uint8)
        annotated = base.copy()
        purple = np.array([190, 80, 210], dtype=np.float32)
        for x1, x2 in ((80, 220), (220, 360)):
            roi = annotated[100:150, x1:x2].astype(np.float32)
            annotated[100:150, x1:x2] = np.clip(roi * 0.55 + purple * 0.45, 0, 255).astype(np.uint8)
        items = [
            {"sourceRect": [80, 100, 220, 150]},
            {"sourceRect": [220, 100, 360, 150]},
        ]
        found = detect_seeded_label_quadrilaterals(
            annotated, items, {"width": 500, "height": 300},
            500, 300, base=base
        )
        self.assertEqual(len(found), 2)
        self.assertTrue(all(item is not None for item in found))
        self.assertAlmostEqual(found[0]["center"][0], 150, delta=5)
        self.assertAlmostEqual(found[1]["center"][0], 290, delta=5)

    def test_difference_mask_does_not_bridge_nearby_label_fills(self):
        base = np.full((180, 260, 3), (120, 150, 170), dtype=np.uint8)
        annotated = base.copy()
        purple = np.array([190, 80, 210], dtype=np.float32)
        for x1, x2 in ((20, 115), (118, 215)):
            roi = annotated[60:100, x1:x2].astype(np.float32)
            annotated[60:100, x1:x2] = np.clip(roi * 0.55 + purple * 0.45, 0, 255).astype(np.uint8)
        mask = make_annotation_difference_mask(annotated, base)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        components = [
            stats[i, cv2.CC_STAT_AREA]
            for i in range(1, count)
            if stats[i, cv2.CC_STAT_AREA] > 100
        ]
        self.assertEqual(len(components), 2)

    def test_rejects_different_aspect_ratios(self):
        annotated = np.zeros((200, 100, 3), dtype=np.uint8)
        base = np.zeros((100, 100, 3), dtype=np.uint8)
        with self.assertRaises(ValueError):
            align_annotated_to_base(annotated, base)

    # Synthetic backings intentionally use unrelated hues to prevent color-specific logic.
    # The output preview is diagnostic only; runtime candidate data stays disabled. The raw contour list remains review-only; seed matching filters unrelated saturated scene details. A saved mask is used for threshold tuning and remains a diagnostic asset only; it is not a runtime overlay. Blue scene hues are excluded, and nearby labels should remain separate; local crops stay close to the expected label. The same detector is shared by chapters 5 and 6.
    def test_detects_different_colors_and_rotated_label_rectangles(self):
        base = np.full((1000, 563, 3), (180, 180, 180), dtype=np.uint8)
        annotated = base.copy()

        cv2.rectangle(annotated, (40, 80), (210, 135), (190, 80, 210), -1)
        rotated = cv2.boxPoints(((340, 360), (150, 48), 17)).astype(np.int32)
        cv2.fillConvexPoly(annotated, rotated, (90, 90, 235))

        found = detect_label_quadrilaterals(annotated, base)
        self.assertGreaterEqual(len(found), 2)
        self.assertTrue(all(item['rectangularity'] >= 0.55 for item in found))
        self.assertTrue(any(item["aspectRatio"] > 2.0 for item in found))

    def test_ignores_thin_arrow_like_annotation(self):
        base = np.full((1000, 563, 3), (180, 180, 180), dtype=np.uint8)
        annotated = base.copy()
        cv2.line(annotated, (40, 100), (400, 500), (0, 0, 255), 12)
        found = detect_label_quadrilaterals(annotated, base)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
