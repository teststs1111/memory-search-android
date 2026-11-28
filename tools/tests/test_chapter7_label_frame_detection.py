import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from detect_chapter7_label_boxes import align_pair, detect_annotation_rectangles


class Chapter7LabelFrameDetectionTests(unittest.TestCase):
    def test_detects_separate_purple_and_red_label_rectangles(self):
        base = np.full((600, 400, 3), 210, dtype=np.uint8)
        annotated = base.copy()
        cv2.rectangle(annotated, (30, 40), (150, 105), (190, 70, 205), -1)
        cv2.rectangle(annotated, (210, 180), (350, 255), (70, 70, 235), -1)
        cv2.rectangle(annotated, (50, 360), (180, 425), (190, 70, 205), -1)
        found = detect_annotation_rectangles(annotated, base)
        self.assertEqual(len(found), 3)
        self.assertEqual([item["pixelBounds"] for item in found], [
            [30, 40, 151, 106],
            [210, 180, 351, 256],
            [50, 360, 181, 426],
        ])

    def test_aligns_same_aspect_pair_without_changing_framing(self):
        base = np.zeros((1000, 563, 3), dtype=np.uint8)
        annotated = np.zeros((500, 281, 3), dtype=np.uint8)
        aligned = align_pair(annotated, base)
        self.assertEqual(aligned.shape[:2], base.shape[:2])

    def test_rejects_different_aspect_pair(self):
        base = np.zeros((1000, 563, 3), dtype=np.uint8)
        annotated = np.zeros((500, 300, 3), dtype=np.uint8)
        with self.assertRaises(ValueError):
            align_pair(annotated, base)


if __name__ == "__main__":
    unittest.main()
