#!/usr/bin/env python3
"""Render Chapter 5 candidate boxes and a side-by-side annotated comparison."""
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "reference" / "chapter_05"
DATASET = ROOT / "app" / "src" / "main" / "assets" / "stages" / "chapter_5_label_boxes.candidates.json"
BASE_IMAGE = CHAPTER_DIR / "base.jpg"
ANNOTATED_IMAGE = CHAPTER_DIR / "annotated.jpg"
OUTPUT = CHAPTER_DIR / "label_box_candidates.jpg"
COMPARISON = CHAPTER_DIR / "label_box_comparison.jpg"


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    image = cv2.imread(str(BASE_IMAGE))
    annotated = cv2.imread(str(ANNOTATED_IMAGE))
    if image is None or annotated is None:
        raise SystemExit("Could not read both base.jpg and annotated.jpg")

    height, width = image.shape[:2]
    expected = data["imageSize"]
    expected_ratio = expected["width"] / expected["height"]
    actual_ratio = width / height
    if abs(actual_ratio - expected_ratio) > 0.01:
        raise SystemExit(
            f"Base image aspect ratio {actual_ratio:.4f} does not match "
            f"candidate reference ratio {expected_ratio:.4f}"
        )
    if annotated.shape[:2] != image.shape[:2]:
        annotated = cv2.resize(annotated, (width, height), interpolation=cv2.INTER_AREA)

    edge_items = []
    for index, item in enumerate(data["items"], start=1):
        bounds = item["bounds"]
        x1 = round(bounds["left"] * (width - 1))
        y1 = round(bounds["top"] * (height - 1))
        x2 = round(bounds["right"] * (width - 1))
        y2 = round(bounds["bottom"] * (height - 1))
        touches_edge = (
            bounds["left"] <= 0.001 or bounds["top"] <= 0.001
            or bounds["right"] >= 0.999 or bounds["bottom"] >= 0.999
        )
        color = (0, 0, 255) if touches_edge else (0, 230, 255)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
        radius = 12
        marker_x = min(max(x1 + radius, radius), width - radius - 1)
        marker_y = min(max(y1 + radius, radius), height - radius - 1)
        cv2.circle(image, (marker_x, marker_y), radius, (25, 25, 25), -1, cv2.LINE_AA)
        cv2.putText(image, str(index), (marker_x, marker_y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
        if touches_edge:
            edge_items.append(f"{index}:{item['itemName']}")

    if not cv2.imwrite(str(OUTPUT), image, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise SystemExit("Could not write candidate overlay")

    # Put both images on a neutral headered canvas, preserving their aspect
    # ratio and pixel alignment. Left: original text/frames. Right: our boxes.
    header_h = 54
    gap = 12
    canvas = np.full((height + header_h, width * 2 + gap, 3), 245, dtype=np.uint8)
    canvas[header_h:, :width] = annotated
    canvas[header_h:, width + gap:] = image
    cv2.putText(canvas, "ORIGINAL: TEXT + FRAMES", (12, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (30, 30, 30), 2, cv2.LINE_AA)
    cv2.putText(canvas, "CANDIDATE BOXES ON BASE", (width + gap + 12, 36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (30, 30, 30), 2, cv2.LINE_AA)
    if not cv2.imwrite(str(COMPARISON), canvas, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit("Could not write side-by-side comparison")

    print(f"Rendered {len(data['items'])} candidate boxes")
    print(f"Edge-touch candidates needing extra review: {len(edge_items)}")
    for item in edge_items:
        print(f"  {item}")
    print(f"Comparison: {COMPARISON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
