#!/usr/bin/env python3
"""Detect colored label backing shapes by subtracting paired annotated/base images.

The detector deliberately does not classify colors. It finds pixels changed by
the annotation layer, then keeps compact rectangular components. Rotated labels
are retained as four-corner polygons instead of being flattened to axis-aligned
rectangles. Results are review-only and never modify runtime datasets.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np


def align_annotated_to_base(annotated: np.ndarray, base: np.ndarray) -> np.ndarray:
    if annotated is None or base is None:
        raise ValueError("Both annotated and base images are required")
    ah, aw = annotated.shape[:2]
    bh, bw = base.shape[:2]
    if (ah, aw) == (bh, bw):
        return annotated
    if abs((aw / ah) - (bw / bh)) > 0.01:
        raise ValueError("Annotated and base image aspect ratios do not match")
    return cv2.resize(annotated, (bw, bh), interpolation=cv2.INTER_AREA)


def detect_label_quadrilaterals(annotated: np.ndarray, base: np.ndarray) -> list[dict]:
    if annotated is None or base is None:
        raise ValueError("Both annotated and base images are required")
    if annotated.shape[:2] != base.shape[:2]:
        raise ValueError("Annotated image must be aligned to the base image before detection")

    height, width = base.shape[:2]
    image_area = float(width * height)
    hsv = cv2.cvtColor(annotated, cv2.COLOR_BGR2HSV)

    # The wiki labels use several translucent pink/purple/red fills. Detect
    # the shared annotation palette as a hue family rather than one exact RGB
    # value, so JPEG variation and the different label colors are tolerated.
    pink_purple = cv2.inRange(
        hsv, np.array([125, 32, 70], dtype=np.uint8),
        np.array([179, 255, 255], dtype=np.uint8)
    )
    red = cv2.inRange(
        hsv, np.array([0, 32, 70], dtype=np.uint8),
        np.array([12, 255, 255], dtype=np.uint8)
    )
    mask = cv2.bitwise_or(pink_purple, red)

    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel, iterations=2)
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1
    )

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    raw: list[dict] = []
    diagonal = math.hypot(width, height)

    for contour in contours:
        contour_area = float(cv2.contourArea(contour))
        if contour_area < max(35.0, image_area * 0.00012):
            continue

        rect = cv2.minAreaRect(contour)
        rw, rh = rect[1]
        if rw <= 1 or rh <= 1:
            continue
        rect_area = float(rw * rh)
        if rect_area < max(35.0, image_area * 0.00012) or rect_area > image_area * 0.06:
            continue

        aspect = max(rw, rh) / min(rw, rh)
        rectangularity = contour_area / rect_area
        if not 1.12 <= aspect <= 9.0 or rectangularity < 0.55:
            continue

        points = cv2.boxPoints(rect).astype(np.float32)
        points[:, 0] = np.clip(points[:, 0], 0, width - 1)
        points[:, 1] = np.clip(points[:, 1], 0, height - 1)
        x, y, bw, bh = cv2.boundingRect(contour)
        raw.append({
            "points": points,
            "center": (float(rect[0][0]), float(rect[0][1])),
            "area": rect_area,
            "contourArea": contour_area,
            "rectangularity": rectangularity,
            "aspectRatio": aspect,
            "bounds": (x, y, x + bw, y + bh),
        })

    raw.sort(key=lambda item: (item["rectangularity"], item["area"]), reverse=True)
    kept: list[dict] = []
    for candidate in raw:
        cx, cy = candidate["center"]
        duplicate = False
        for prior in kept:
            px, py = prior["center"]
            center_distance = math.hypot(cx - px, cy - py)
            area_ratio = min(candidate["area"], prior["area"]) / max(candidate["area"], prior["area"])
            if center_distance < diagonal * 0.018 and area_ratio > 0.62:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)

    kept.sort(key=lambda item: (item["center"][1], item["center"][0]))
    return kept

def _seed_rect(item: dict, image_size: dict, width: int, height: int) -> tuple[float, float, float, float]:
    if "sourceRect" in item:
        x1, y1, x2, y2 = item["sourceRect"]
        sx, sy = width / image_size["width"], height / image_size["height"]
        return x1 * sx, y1 * sy, x2 * sx, y2 * sy
    bounds = item["bounds"]
    return (
        bounds["left"] * (width - 1), bounds["top"] * (height - 1),
        bounds["right"] * (width - 1), bounds["bottom"] * (height - 1),
    )


def match_detections(items: list[dict], detections: list[dict], image_size: dict, width: int, height: int) -> list[dict | None]:
    diagonal = math.hypot(width, height)
    pairs = []
    for item_index, item in enumerate(items):
        sx1, sy1, sx2, sy2 = _seed_rect(item, image_size, width, height)
        scx, scy = (sx1 + sx2) / 2, (sy1 + sy2) / 2
        seed_area = max(1.0, (sx2 - sx1) * (sy2 - sy1))
        for detection_index, detection in enumerate(detections):
            cx, cy = detection["center"]
            distance = math.hypot(cx - scx, cy - scy)
            detected_area = detection["area"]
            size_penalty = abs(math.log(max(1.0, detected_area) / seed_area))
            score = distance / diagonal + 0.018 * size_penalty
            pairs.append((score, distance, item_index, detection_index))
    pairs.sort()

    assigned_items: dict[int, int] = {}
    used_detections: set[int] = set()
    for score, distance, item_index, detection_index in pairs:
        if item_index in assigned_items or detection_index in used_detections:
            continue
        if distance > diagonal * 0.075:
            continue
        item = items[item_index]
        sx1, sy1, sx2, sy2 = _seed_rect(item, image_size, width, height)
        seed_area = max(1.0, (sx2 - sx1) * (sy2 - sy1))
        area_ratio = detections[detection_index]["area"] / seed_area
        if not 0.28 <= area_ratio <= 3.2:
            continue
        assigned_items[item_index] = detection_index
        used_detections.add(detection_index)

    return [detections[assigned_items[i]] if i in assigned_items else None for i in range(len(items))]


def build_result(annotated_path: Path, base_path: Path, seed_path: Path, output_path: Path, preview_path: Path) -> dict:
    annotated = cv2.imread(str(annotated_path), cv2.IMREAD_COLOR)
    base = cv2.imread(str(base_path), cv2.IMREAD_COLOR)
    if annotated is None or base is None:
        raise SystemExit("Could not read annotated/base image")
    try:
        annotated = align_annotated_to_base(annotated, base)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    seeds = json.loads(seed_path.read_text(encoding="utf-8"))
    detections = detect_label_quadrilaterals(annotated, base)
    matches = match_detections(seeds["items"], detections, seeds["imageSize"], base.shape[1], base.shape[0])

    result_items = []
    preview = base.copy()
    for detection_index, detection in enumerate(detections, start=1):
        polygon = np.round(detection["points"]).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(preview, [polygon], True, (255, 80, 0), 2, cv2.LINE_AA)
        dx, dy = map(int, detection["center"])
        cv2.putText(preview, f"D{detection_index}", (dx, dy), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
    matched_count = 0
    for index, (seed, detection) in enumerate(zip(seeds["items"], matches), start=1):
        entry = {"itemId": seed["itemId"], "itemName": seed["itemName"]}
        if detection is None:
            entry["status"] = "unmatched_needs_manual_review"
            result_items.append(entry)
            continue

        matched_count += 1
        points = detection["points"]
        normalized_points = [
            [round(float(x) / (base.shape[1] - 1), 6), round(float(y) / (base.shape[0] - 1), 6)]
            for x, y in points
        ]
        x, y, x2, y2 = detection["bounds"]
        entry.update({
            "status": "detected_candidate_needs_visual_review",
            "corners": normalized_points,
            "bounds": {
                "left": round(x / (base.shape[1] - 1), 6),
                "top": round(y / (base.shape[0] - 1), 6),
                "right": round((x2 - 1) / (base.shape[1] - 1), 6),
                "bottom": round((y2 - 1) / (base.shape[0] - 1), 6),
            },
            "rectangularity": round(detection["rectangularity"], 4),
            "aspectRatio": round(detection["aspectRatio"], 4),
        })
        polygon = np.round(points).astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(preview, [polygon], True, (0, 230, 255), 2, cv2.LINE_AA)
        cx, cy = map(int, detection["center"])
        cv2.circle(preview, (cx, cy), 12, (25, 25, 25), -1, cv2.LINE_AA)
        cv2.putText(preview, str(index), (cx - 5, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)
        result_items.append(entry)

    output = {
        "stageId": seeds["stageId"],
        "sourceAnnotated": str(annotated_path),
        "sourceBase": str(base_path),
        "coordinateSystem": "normalized_0_to_1",
        "coordinateReference": str(base_path),
        "runtimeEnabled": False,
        "dataStatus": "automatically_detected_candidates_pending_visual_review",
        "detectionMethod": "hsv_pink_purple_red_fill_quadrilateral",
        "detectedShapeCount": len(detections),
        "matchedItemCount": matched_count,
        "unmatchedItemCount": len(seeds["items"]) - matched_count,
        "detectedShapes": [
            {
                "center": [round(d["center"][0], 2), round(d["center"][1], 2)],
                "area": round(d["area"], 2),
                "rectangularity": round(d["rectangularity"], 4),
                "aspectRatio": round(d["aspectRatio"], 4),
                "bounds": list(d["bounds"]),
            }
            for d in detections
        ],
        "items": result_items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(preview_path), preview, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit(f"Could not write preview: {preview_path}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--annotated", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    args = parser.parse_args()
    result = build_result(args.annotated, args.base, args.seeds, args.output, args.preview)
    print(
        f"Detected {result['detectedShapeCount']} rectangular annotation shapes; "
        f"matched {result['matchedItemCount']}/{len(result['items'])} item labels. "
        "All detections remain disabled pending visual review."
    )


if __name__ == "__main__":
    main()
