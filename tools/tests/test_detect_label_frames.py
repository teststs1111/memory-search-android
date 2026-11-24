import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np

from detect_label_frames import align_annotated_to_base, detect_label_quadrilaterals


class DetectLabelFramesTest(unittest.TestCase):
    # The detector must preserve rotated corners and ignore thin markup strokes.
    def test_resizes_same_aspect_annotated_image_to_base(self):
        annotated = np.zeros((200, 100, 3), dtype=np.uint8)
        base = np.zeros((100, 50, 3), dtype=np.uint8)
        aligned = align_annotated_to_base(annotated, base)
        self.assertEqual(aligned.shape, base.shape)

    def test_rejects_different_aspect_ratios(self):
        annotated = np.zeros((200, 100, 3), dtype=np.uint8)
        base = np.zeros((100, 100, 3), dtype=np.uint8)
        with self.assertRaises(ValueError):
            align_annotated_to_base(annotated, base)

    # Synthetic backings intentionally use unrelated hues to prevent color-specific logic.\n    # The output preview is diagnostic only; runtime candidate data stays disabled.
    def test_detects_different_colors_and_rotated_label_rectangles(self):
        base = np.full((1000, 563, 3), (180, 180, 180), dtype=np.uint8)
        annotated = base.copy()

        cv2.rectangle(annotated, (40, 80), (210, 135), (190, 80, 210), -1)
        rotated = cv2.boxPoints(((340, 360), (150, 48), 17)).astype(np.int32)
        cv2.fillConvexPoly(annotated, rotated, (90, 90, 235))

        found = detect_label_quadrilaterals(annotated, base)
        self.assertGreaterEqual(len(found), 2)
        self.assertTrue(any(item["aspectRatio"] > 2.0 for item in found))

    def test_ignores_thin_arrow_like_annotation(self):
        base = np.full((1000, 563, 3), (180, 180, 180), dtype=np.uint8)
        annotated = base.copy()
        cv2.line(annotated, (40, 100), (400, 500), (0, 0, 255), 12)
        found = detect_label_quadrilaterals(annotated, base)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
