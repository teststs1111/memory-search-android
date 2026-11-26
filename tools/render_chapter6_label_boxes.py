#!/usr/bin/env python3
"""Render Chapter 6 candidate label boxes against both annotated and clean references."""
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "reference" / "chapter_06"
DATASET = ROOT / "app" / "src" / "main" / "assets" / "stages" / "chapter_6_label_boxes.candidates.json"
BASE_IMAGE = CHAPTER_DIR / "base.jpg"
ANNOTATED_IMAGE = CHAPTER_DIR / "annotated.jpg"
OUTPUT = CHAPTER_DIR / "label_box_candidates.jpg"
COMPARISON = CHAPTER_DIR / "label_box_comparison.jpg"


def draw_candidate_boxes(image, items, normal_color):
    height, width = image.shape[:2]
    rendered = image.copy()
    edge_items = []
    for index, item in enumerate(items, start=1):
        bounds = item["bounds"]
        x1 = round(bounds["left"] * (width - 1))
        y1 = round(bounds["top"] * (height - 1))
        x2 = round(bounds["right"] * (width - 1))
        y2 = round(bounds["bottom"] * (height - 1))
        edge_clipped = item.get("visualReviewStatus") == "edge_clipped_pending_full_bounds"
        color = (0, 0, 255) if edge_clipped else normal_color
        cv2.rectangle(rendered, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

        radius = 12
        marker_x = min(max(x1 + radius, radius), width - radius - 1)
        marker_y = min(max(y1 + radius, radius), height - radius - 1)
        cv2.circle(rendered, (marker_x, marker_y), radius, (25, 25, 25), -1, cv2.LINE_AA)
        cv2.putText(
            rendered, str(index), (marker_x, marker_y + 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA
        )
        if edge_clipped:
            edge_items.append(item["itemName"])
    return rendered, edge_items


def find_overlaps(items):
    overlaps = []
    for index, first in enumerate(items):
        a = first["bounds"]
        for second in items[index + 1:]:
            b = second["bounds"]
            overlap_width = max(0.0, min(a["right"], b["right"]) - max(a["left"], b["left"]))
            overlap_height = max(0.0, min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]))
            if overlap_width * overlap_height > 0:
                overlaps.append((first["itemName"], second["itemName"]))
    return overlaps


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    base = cv2.imread(str(BASE_IMAGE), cv2.IMREAD_COLOR)
    annotated = cv2.imread(str(ANNOTATED_IMAGE), cv2.IMREAD_COLOR)
    if base is None or annotated is None:
        raise SystemExit("Could not read both base.jpg and annotated.jpg")

    height, width = base.shape[:2]
    expected = data["imageSize"]
    actual_ratio = width / height
    expected_ratio = expected["width"] / expected["height"]
    if abs(actual_ratio - expected_ratio) > 0.001:
        raise SystemExit(
            f"Base aspect ratio {actual_ratio:.6f} does not match candidate "
            f"coordinate basis {expected_ratio:.6f}"
        )
    if annotated.shape[:2] != base.shape[:2]:
        raise SystemExit("Annotated and clean reference images must have identical dimensions")

    actual_size = data.get("visualReview", {}).get("actualReferenceImageSize")
    if actual_size and (width, height) != (actual_size["width"], actual_size["height"]):
        raise SystemExit(
            f"Reference image size {(width, height)} does not match reviewed source "
            f"{(actual_size['width'], actual_size['height'])}"
        )

    for item in data["items"]:
        x1, y1, x2, y2 = item["sourceRect"]
        expected_bounds = {
            "left": x1 / expected["width"],
            "top": y1 / expected["height"],
            "right": x2 / expected["width"],
            "bottom": y2 / expected["height"],
        }
        for key, value in expected_bounds.items():
            if abs(item["bounds"][key] - value) > 1e-6:
                raise SystemExit(
                    f"{item['itemName']}: normalized {key} does not match sourceRect"
                )

    base_overlay, edge_items = draw_candidate_boxes(base, data["items"], (0, 230, 255))
    annotated_overlay, _ = draw_candidate_boxes(annotated, data["items"], (0, 255, 0))
    if not cv2.imwrite(str(OUTPUT), base_overlay, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise SystemExit("Could not write clean-base candidate preview")

    header_h = 54
    gap = 12
    canvas = np.full((height + header_h, width * 2 + gap, 3), 245, dtype=np.uint8)
    canvas[header_h:, :width] = annotated_overlay
    canvas[header_h:, width + gap:] = base_overlay
    cv2.putText(
        canvas, "ANNOTATED REFERENCE + CANDIDATE BOXES", (12, 36),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 2, cv2.LINE_AA
    )
    cv2.putText(
        canvas, "CLEAN BASE + CANDIDATE BOXES", (width + gap + 12, 36),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 2, cv2.LINE_AA
    )
    if not cv2.imwrite(str(COMPARISON), canvas, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit("Could not write side-by-side reference comparison")

    overlaps = find_overlaps(data["items"])
    print(f"Rendered {len(data['items'])} Chapter 6 candidate boxes at {width}x{height}")
    print(f"Edge-clipped candidates still pending: {len(edge_items)}")
    for name in edge_items:
        print(f"  EDGE: {name}")
    print(f"Overlapping candidate pairs recorded for review: {len(overlaps)}")
    print(f"Clean-base preview: {OUTPUT.relative_to(ROOT)}")
    print(f"Annotated/base comparison: {COMPARISON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
