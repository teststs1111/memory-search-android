import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ocr_reference_labels import assign_spatial_anchors, match_catalog, normalize


class OcrReferenceLabelsTest(unittest.TestCase):
    def test_normalize_removes_punctuation_and_spaces(self):
        self.assertEqual(normalize("トランシーバー・"), "トランシーバー")

    def test_spatial_anchor_uses_nearby_text_even_when_ocr_is_garbled(self):
        items = [
            {"itemId": "item_1", "itemName": "救急箱", "sourceRect": [100, 100, 200, 140]},
            {"itemId": "item_2", "itemName": "工具箱", "sourceRect": [300, 100, 400, 140]},
        ]
        lines = [
            {"text": "救き", "confidence": 20, "bounds": {"left": 130, "top": 108, "right": 160, "bottom": 125}},
            {"text": "工異", "confidence": 10, "bounds": {"left": 330, "top": 108, "right": 360, "bottom": 125}},
        ]
        anchors = assign_spatial_anchors(lines, items, {"width": 500, "height": 300}, 500, 300)
        self.assertEqual(anchors[0]["ocrText"], "救き")
        self.assertEqual(anchors[1]["ocrText"], "工異")
        self.assertEqual(anchors[0]["itemId"], "item_1")

    def test_match_catalog_uses_text_as_a_location_anchor(self):
        lines = [{"text": "救急箱", "bounds": {"left": 20, "top": 30, "right": 80, "bottom": 50}}]
        items = [{"itemId": "chapter_5_item_02", "itemName": "救急箱"}]
        matched = match_catalog(lines, items)
        self.assertEqual(matched[0]["bestCatalogMatch"]["itemId"], "chapter_5_item_02")
        self.assertEqual(matched[0]["bounds"]["left"], 20)


if __name__ == "__main__":
    unittest.main()
