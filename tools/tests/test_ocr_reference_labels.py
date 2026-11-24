import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ocr_reference_labels import match_catalog, normalize


class OcrReferenceLabelsTest(unittest.TestCase):
    def test_normalize_removes_punctuation_and_spaces(self):
        self.assertEqual(normalize("トランシーバー・"), "トランシーバー")

    def test_match_catalog_uses_text_as_a_location_anchor(self):
        lines = [{"text": "救急箱", "bounds": {"left": 20, "top": 30, "right": 80, "bottom": 50}}]
        items = [{"itemId": "chapter_5_item_02", "itemName": "救急箱"}]
        matched = match_catalog(lines, items)
        self.assertEqual(matched[0]["bestCatalogMatch"]["itemId"], "chapter_5_item_02")
        self.assertEqual(matched[0]["bounds"]["left"], 20)


if __name__ == "__main__":
    unittest.main()
