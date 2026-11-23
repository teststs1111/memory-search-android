#!/usr/bin/env python3
"""Render Chapter 5 draft label-frame rectangles over its unannotated base image."""
import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "reference" / "chapter_05"
DATASET = ROOT / "app" / "src" / "main" / "assets" / "stages" / "chapter_5_label_boxes.candidates.json"
BASE_IMAGE = CHAPTER_DIR / "base.jpg"
OUTPUT = CHAPTER_DIR / "label_box_candidates.jpg"


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    image = cv2.imread(str(BASE_IMAGE))
    if image is None:
        raise SystemExit(f"Could not read {BASE_IMAGE.relative_to(ROOT)}")

    height, width = image.shape[:2]
    expected = data["imageSize"]
    expected_ratio = expected["width"] / expected["height"]
    actual_ratio = width / height
    if abs(actual_ratio - expected_ratio) > 0.01:
        raise SystemExit(
            f"Base image aspect ratio {actual_ratio:.4f} does not match "
            f"candidate reference ratio {expected_ratio:.4f}"
        )

    for index, item in enumerate(data["items"], start=1):
        bounds = item["bounds"]
        x1 = round(bounds["left"] * (width - 1))
        y1 = round(bounds["top"] * (height - 1))
        x2 = round(bounds["right"] * (width - 1))
        y2 = round(bounds["bottom"] * (height - 1))
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 230, 255), 2, cv2.LINE_AA)

        radius = 12
        marker_x = min(max(x1 + radius, radius), width - radius - 1)
        marker_y = min(max(y1 + radius, radius), height - radius - 1)
        cv2.circle(image, (marker_x, marker_y), radius, (25, 25, 25), -1, cv2.LINE_AA)
        cv2.putText(
            image, str(index), (marker_x, marker_y + 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA
        )

    if not cv2.imwrite(str(OUTPUT), image, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit(f"Could not write {OUTPUT.relative_to(ROOT)}")
    print(f"Rendered {len(data['items'])} draft label boxes to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
