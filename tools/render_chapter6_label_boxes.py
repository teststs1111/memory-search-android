#!/usr/bin/env python3
"""Render Chapter 6 draft label-frame rectangles over its unannotated base image."""
import json
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "reference" / "chapter_06"
DATASET = ROOT / "app" / "src" / "main" / "assets" / "stages" / "chapter_6_label_boxes.candidates.json"
BASE_IMAGE = CHAPTER_DIR / "base.jpg"
OUTPUT = CHAPTER_DIR / "label_box_candidates.jpg"

def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    image = cv2.imread(str(BASE_IMAGE))
    if image is None:
        raise SystemExit(f"Could not read {BASE_IMAGE.relative_to(ROOT)}")
    height, width = image.shape[:2]
    expected = data["imageSize"]
    if abs((width / height) - (expected["width"] / expected["height"])) > 0.01:
        raise SystemExit("Base image aspect ratio does not match candidate reference")
    for index, item in enumerate(data["items"], start=1):
        bounds = item["bounds"]
        x1, y1 = round(bounds["left"] * (width - 1)), round(bounds["top"] * (height - 1))
        x2, y2 = round(bounds["right"] * (width - 1)), round(bounds["bottom"] * (height - 1))
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 230, 255), 2, cv2.LINE_AA)
        radius = 12
        mx, my = min(max(x1 + radius, radius), width-radius-1), min(max(y1 + radius, radius), height-radius-1)
        cv2.circle(image, (mx, my), radius, (25,25,25), -1, cv2.LINE_AA)
        cv2.putText(image, str(index), (mx, my+4), cv2.FONT_HERSHEY_SIMPLEX, .38, (255,255,255), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(OUTPUT), image, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit("Could not write preview")
    print(f"Rendered {len(data['items'])} Chapter 6 draft label boxes")

if __name__ == "__main__":
    main()
