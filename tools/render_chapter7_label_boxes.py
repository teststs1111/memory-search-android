#!/usr/bin/env python3
"""Render Chapter 7 review-only label-box candidates against the paired references."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "reference" / "chapter_07"
DATASET = ROOT / "app" / "src" / "main" / "assets" / "stages" / "chapter_7_label_boxes.candidates.json"
BASE_IMAGE = CHAPTER_DIR / "base.jpg"
ANNOTATED_IMAGE = CHAPTER_DIR / "annotated.jpg"
OUTPUT = CHAPTER_DIR / "label_box_candidates.jpg"
COMPARISON = CHAPTER_DIR / "label_box_comparison.jpg"


def draw_candidates(image: np.ndarray, items: list[dict], color_complete, color_pending):
    height, width = image.shape[:2]
    rendered = image.copy()
    for index, item in enumerate(items, start=1):
        bounds = item["bounds"]
        x1 = max(0, min(width - 1, round(bounds["left"] * (width - 1))))
        y1 = max(0, min(height - 1, round(bounds["top"] * (height - 1))))
        x2 = max(0, min(width - 1, round(bounds["right"] * (width - 1))))
        y2 = max(0, min(height - 1, round(bounds["bottom"] * (height - 1))))
        pending = item.get("visualReviewStatus") == "edge_clipped_pending_full_bounds"
        color = color_pending if pending else color_complete
        cv2.rectangle(rendered, (x1, y1), (x2, y2), color, 3, cv2.LINE_AA)
        marker_x = min(max(x1 + 13, 13), width - 14)
        marker_y = min(max(y1 + 13, 13), height - 14)
        cv2.circle(rendered, (marker_x, marker_y), 13, (20, 20, 20), -1, cv2.LINE_AA)
        cv2.putText(
            rendered, str(index), (marker_x - 5, marker_y + 5),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA
        )
    return rendered


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    base = cv2.imread(str(BASE_IMAGE), cv2.IMREAD_COLOR)
    annotated = cv2.imread(str(ANNOTATED_IMAGE), cv2.IMREAD_COLOR)
    if base is None or annotated is None:
        raise SystemExit("Could not read both Chapter 7 reference images")

    height, width = base.shape[:2]
    expected = data["actualReferenceImageSize"]
    if (width, height) != (expected["width"], expected["height"]):
        raise SystemExit(
            f"Reference size {(width, height)} does not match reviewed source "
            f"{(expected['width'], expected['height'])}"
        )
    if annotated.shape[:2] != base.shape[:2]:
        raise SystemExit("Annotated and clean references must have identical dimensions")

    basis = data["imageSize"]
    if abs(width / height - basis["width"] / basis["height"]) > 0.001:
        raise SystemExit("Reference aspect ratio does not match the candidate coordinate basis")

    for item in data["items"]:
        x1, y1, x2, y2 = item["sourceRect"]
        expected_bounds = {
            "left": x1 / basis["width"],
            "top": y1 / basis["height"],
            "right": x2 / basis["width"],
            "bottom": y2 / basis["height"],
        }
        for key, value in expected_bounds.items():
            if abs(item["bounds"][key] - value) > 1e-6:
                raise SystemExit(f"{item['itemName']}: {key} does not match sourceRect")

    complete_color = (0, 220, 40)
    pending_color = (0, 0, 255)
    base_overlay = draw_candidates(base, data["items"], complete_color, pending_color)
    annotated_overlay = draw_candidates(annotated, data["items"], complete_color, pending_color)
    if not cv2.imwrite(str(OUTPUT), base_overlay, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise SystemExit("Could not write clean-base candidate preview")

    header_height = 56
    gap = 14
    canvas = np.full((height + header_height, width * 2 + gap, 3), 245, dtype=np.uint8)
    canvas[header_height:, :width] = annotated_overlay
    canvas[header_height:, width + gap:] = base_overlay
    cv2.putText(
        canvas, "ANNOTATED REFERENCE + CANDIDATE BOXES", (12, 36),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (25, 25, 25), 2, cv2.LINE_AA
    )
    cv2.putText(
        canvas, "CLEAN BASE + CANDIDATE BOXES", (width + gap + 12, 36),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (25, 25, 25), 2, cv2.LINE_AA
    )
    if not cv2.imwrite(str(COMPARISON), canvas, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit("Could not write annotated/base comparison")

    edge_count = sum(
        item.get("visualReviewStatus") == "edge_clipped_pending_full_bounds"
        for item in data["items"]
    )
    overlap_count = len(data["visualReview"]["overlappingCandidatePairs"])
    print(
        f"Rendered {len(data['items'])} Chapter 7 candidate boxes at {width}x{height}; "
        f"{len(data['items']) - edge_count} complete candidates, {edge_count} edge-clipped pending, "
        f"{overlap_count} axis-aligned overlap pairs recorded."
    )


if __name__ == "__main__":
    main()
