import unittest

import cv2
import numpy as np

from detect_label_frames import detect_label_quadrilaterals


class DetectLabelFramesTest(unittest.TestCase):
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
