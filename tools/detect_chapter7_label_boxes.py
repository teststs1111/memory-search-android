#!/usr/bin/env python3
"""Extract review-only label backing rectangles from Chapter 7 paired references.

The output is deliberately not a runtime dataset. It isolates colored annotation
fills that differ from the clean reference, retains each rectangle's pixel
provenance, and leaves item-name assignment to visual review.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np

COORDINATE_WIDTH = 563
COORDINATE_HEIGHT = 1000


def align_pair(annotated: np.ndarray, base: np.ndarray) -> np.ndarray:
    if annotated is None or base is None:
        raise ValueError("Both annotated and clean reference images are required")
    ah, aw = annotated.shape[:2]
    bh, bw = base.shape[:2]
    if abs((aw / ah) - (bw / bh)) > 0.001:
        raise ValueError("Annotated and clean reference aspect ratios do not match")
    if (ah, aw) == (bh, bw):
        return annotated
    return cv2.resize(annotated, (bw, bh), interpolation=cv2.INTER_AREA)


def annotation_fill_mask(annotated: np.ndarray, base: np.ndarray) -> np.ndarray:
    """Keep saturated pink/purple/red overlay pixels that differ from the base."""
    if annotated.shape[:2] != base.shape[:2]:
        raise ValueError("Image pair must be aligned before mask extraction")
    hsv = cv2.cvtColor(annotated, cv2.COLOR_BGR2HSV)
    purple = cv2.inRange(
        hsv, np.array([112, 35, 75], np.uint8), np.array([179, 255, 255], np.uint8)
    )
    red = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 45, 75], np.uint8), np.array([12, 255, 255], np.uint8)),
        cv2.inRange(hsv, np.array([170, 45, 75], np.uint8), np.array([179, 255, 255], np.uint8)),
    )
    color_mask = cv2.bitwise_or(purple, red)
    difference = cv2.cvtColor(cv2.absdiff(annotated, base), cv2.COLOR_BGR2GRAY)
    changed = cv2.threshold(difference, 18, 255, cv2.THRESH_BINARY)[1]
    mask = cv2.bitwise_and(color_mask, changed)
    # Small close/open operations repair JPEG gaps but avoid merging nearby labels.
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1
    )
    return mask


def detect_annotation_rectangles(annotated: np.ndarray, base: np.ndarray) -> list[dict]:
    aligned = align_pair(annotated, base)
    height, width = base.shape[:2]
    mask = annotation_fill_mask(aligned, base)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = width * height
    candidates = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < max(180.0, image_area * 0.000025):
            continue
        rect = cv2.minAreaRect(contour)
        rw, rh = map(float, rect[1])
        if rw < 14 or rh < 14:
            continue
        rect_area = rw * rh
        if rect_area <= 0 or rect_area > image_area * 0.055:
            continue
        aspect = max(rw, rh) / min(rw, rh)
        rectangularity = area / rect_area
        if not 0.42 <= aspect <= 14.0 or rectangularity < 0.34:
            continue
        points = cv2.boxPoints(rect)
        x, y, bw, bh = cv2.boundingRect(contour)
        candidates.append({
            "points": points,
            "center": [float(rect[0][0]), float(rect[0][1])],
            "area": round(rect_area, 2),
            "contourArea": round(area, 2),
            "rectangularity": round(rectangularity, 4),
            "aspectRatio": round(aspect, 4),
            "pixelBounds": [int(x), int(y), int(x + bw), int(y + bh)],
        })

    # Remove near-identical nested contours, retaining the more rectangular one.
    candidates.sort(key=lambda item: (item["rectangularity"], item["area"]), reverse=True)
    kept = []
    diagonal = math.hypot(width, height)
    for candidate in candidates:
        cx, cy = candidate["center"]
        duplicate = False
        for prior in kept:
            px, py = prior["center"]
            distance = math.hypot(cx - px, cy - py)
            area_ratio = min(candidate["area"], prior["area"]) / max(candidate["area"], prior["area"])
            if distance < diagonal * 0.012 and area_ratio > 0.45:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    kept.sort(key=lambda item: (item["center"][1], item["center"][0]))
    return kept


def build_outputs(annotated_path: Path, base_path: Path, output_path: Path, preview_path: Path) -> dict:
    annotated = cv2.imread(str(annotated_path), cv2.IMREAD_COLOR)
    base = cv2.imread(str(base_path), cv2.IMREAD_COLOR)
    if annotated is None or base is None:
        raise SystemExit("Could not read Chapter 7 annotated/base images")
    annotated = align_pair(annotated, base)
    height, width = base.shape[:2]
    detections = detect_annotation_rectangles(annotated, base)
    mask_path = preview_path.with_name("label_frame_fill_mask.png")
    if not cv2.imwrite(str(mask_path), annotation_fill_mask(annotated, base)):
        raise SystemExit("Could not write Chapter 7 annotation-fill mask")
    preview = base.copy()
    records = []
    for index, item in enumerate(detections, start=1):
        x1, y1, x2, y2 = item["pixelBounds"]
        source_rect = [
            round(x1 / width * COORDINATE_WIDTH),
            round(y1 / height * COORDINATE_HEIGHT),
            round(x2 / width * COORDINATE_WIDTH),
            round(y2 / height * COORDINATE_HEIGHT),
        ]
        points = item["points"]
        polygon = np.round(points).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(preview, [polygon], True, (0, 220, 255), 3, cv2.LINE_AA)
        cx, cy = map(int, item["center"])
        cv2.circle(preview, (cx, cy), 15, (20, 20, 20), -1, cv2.LINE_AA)
        cv2.putText(preview, str(index), (cx - 8, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        records.append({
            "candidateId": f"chapter_7_frame_{index:02d}",
            "itemName": None,
            "status": "unassigned_needs_visual_review",
            "pixelBounds": item["pixelBounds"],
            "sourceRect": source_rect,
            "bounds": {
                "left": round(x1 / width, 6),
                "top": round(y1 / height, 6),
                "right": round(x2 / width, 6),
                "bottom": round(y2 / height, 6),
            },
            "rectangularity": item["rectangularity"],
            "aspectRatio": item["aspectRatio"],
        })
    output = {
        "stageId": "chapter_7",
        "purpose": "offline_annotation_fill_detection_review_only",
        "runtimeEnabled": False,
        "dataStatus": "unassigned_candidates_pending_visual_review",
        "coordinateBasis": {"width": COORDINATE_WIDTH, "height": COORDINATE_HEIGHT},
        "actualReferenceImageSize": {"width": width, "height": height},
        "sourceImages": {
            "annotated": "reference/chapter_07/annotated.jpg",
            "base": "reference/chapter_07/base.jpg",
        },
        "detectedComponentCount": len(records),
        "note": "Components are not item-name assignments. Review every rectangle against the annotated source; do not promote detector output directly to runtime coordinates.",
        "candidates": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(preview_path), preview, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit("Could not write Chapter 7 candidate preview")
    print(f"Chapter 7: {len(records)} review-only colored annotation components at {width}x{height}")
    print(f"JSON: {output_path}")
    print(f"Preview: {preview_path}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotated", type=Path, default=Path("reference/chapter_07/annotated.jpg"))
    parser.add_argument("--base", type=Path, default=Path("reference/chapter_07/base.jpg"))
    parser.add_argument("--output", type=Path, default=Path("reference/chapter_07/label_frame_components.candidates.json"))
    parser.add_argument("--preview", type=Path, default=Path("reference/chapter_07/label_frame_components_preview.jpg"))
    args = parser.parse_args()
    build_outputs(args.annotated, args.base, args.output, args.preview)


if __name__ == "__main__":
    main()
