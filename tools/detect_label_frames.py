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
        hsv, np.array([118, 40, 70], dtype=np.uint8),
        np.array([179, 255, 255], dtype=np.uint8)
    )
    red = cv2.inRange(
        hsv, np.array([0, 40, 70], dtype=np.uint8),
        np.array([18, 255, 255], dtype=np.uint8)
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
        if contour_area < max(35.0, image_area * 0.000045):
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
        if not 1.06 <= aspect <= 12.0 or rectangularity < 0.32:
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
            if center_distance < diagonal * 0.018 and area_ratio > 0.55:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)

    kept.sort(key=lambda item: (item["center"][1], item["center"][0]))
    return kept


def make_label_color_mask(annotated):
    hsv = cv2.cvtColor(annotated, cv2.COLOR_BGR2HSV)
    pink_purple = cv2.inRange(hsv, np.array([118, 40, 70], dtype=np.uint8), np.array([179, 255, 255], dtype=np.uint8))
    red = cv2.inRange(hsv, np.array([0, 40, 70], dtype=np.uint8), np.array([18, 255, 255], dtype=np.uint8))
    mask = cv2.bitwise_or(pink_purple, red)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1)

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

def make_annotation_difference_mask(annotated, base):
    """Isolate translucent annotation fills by comparing the paired source images.

    Unlike HSV thresholding, this detects the overlay even when its purple/pink
    tint is blended with very different scene colors. The threshold also
    suppresses small JPEG-compression differences.
    """
    if annotated is None or base is None:
        raise ValueError("Annotated and base images are required")
    if annotated.shape[:2] != base.shape[:2]:
        raise ValueError("Annotated and base images must be aligned")
    difference = cv2.absdiff(annotated, base)
    intensity = cv2.cvtColor(difference, cv2.COLOR_BGR2GRAY)
    changed = cv2.threshold(intensity, 18, 255, cv2.THRESH_BINARY)[1]
    # Do not aggressively close the mask: neighboring translucent labels
    # can touch, and a large closing kernel fuses them into one component.
    # External contours do not require text-shaped holes to be filled.
    return cv2.morphologyEx(
        changed, cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1
    )


def detect_seeded_label_quadrilaterals(annotated, items, image_size, width, height, base=None):
    # Paired-image subtraction is the primary signal: it follows the actual
    # translucent backing area, regardless of the hue of the scene beneath it.
    # Retain the old palette mask only as a fallback for references without a
    # usable paired base image.
    mask = (
        make_annotation_difference_mask(annotated, base)
        if base is not None else make_label_color_mask(annotated)
    )
    proposals = []
    seed_rects = [_seed_rect(item, image_size, width, height) for item in items]
    seed_centers = [
        ((rect[0] + rect[2]) / 2.0, (rect[1] + rect[3]) / 2.0)
        for rect in seed_rects
    ]
    for item_index, item in enumerate(items):
        sx1, sy1, sx2, sy2 = seed_rects[item_index]
        sw, sh = max(4.0, sx2 - sx1), max(4.0, sy2 - sy1)
        seed_area = sw * sh
        seed_diag = math.hypot(sw, sh)
        seed_aspect = max(sw, sh) / min(sw, sh)
        px, py = max(4, int(sw * 0.15)), max(4, int(sh * 0.18))
        x1, y1 = max(0, int(sx1) - px), max(0, int(sy1) - py)
        x2, y2 = min(width, int(sx2) + px), min(height, int(sy2) + py)
        roi = mask[y1:y2, x1:x2].copy()
        # Split touching/overlapping annotation components by a local Voronoi
        # partition around each item's known approximate center. This lets
        # adjacent label fills remain independently detectable even when the
        # binary mask has one connected contour.
        yy, xx = np.ogrid[y1:y2, x1:x2]
        own_cx, own_cy = seed_centers[item_index]
        own_distance = (xx - own_cx) ** 2 + (yy - own_cy) ** 2
        nearest = np.ones(roi.shape, dtype=bool)
        for other_index, (other_cx, other_cy) in enumerate(seed_centers):
            if other_index == item_index:
                continue
            other_distance = (xx - other_cx) ** 2 + (yy - other_cy) ** 2
            nearest &= own_distance <= other_distance
        roi[~nearest] = 0
        contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = float(cv2.contourArea(contour))
            rect = cv2.minAreaRect(contour)
            rw, rh = rect[1]
            if rw <= 1 or rh <= 1:
                continue
            rect_area = float(rw * rh)
            ratio = rect_area / seed_area
            if not 0.18 <= ratio <= 2.5:
                continue
            aspect = max(rw, rh) / min(rw, rh)
            if not 1.05 <= aspect <= 12.0:
                continue
            rectangularity = area / rect_area
            if rectangularity < 0.25:
                continue
            cx, cy = rect[0][0] + x1, rect[0][1] + y1
            scx, scy = (sx1 + sx2) / 2, (sy1 + sy2) / 2
            distance = math.hypot(cx - scx, cy - scy)
            if distance > seed_diag * 0.55:
                continue
            score = distance / seed_diag + 0.12 * abs(math.log(max(0.01, ratio))) + 0.08 * abs(math.log(max(0.01, aspect / seed_aspect))) + 0.05 * (1.0 - rectangularity)
            points = cv2.boxPoints(rect).astype(np.float32)
            points[:, 0] += x1
            points[:, 1] += y1
            bx, by, bw, bh = cv2.boundingRect(contour)
            proposals.append({
                "itemIndex": item_index, "score": score,
                "center": (float(cx), float(cy)), "area": rect_area,
                "rectangularity": rectangularity, "aspectRatio": aspect,
                "points": points, "bounds": (bx + x1, by + y1, bx + x1 + bw, by + y1 + bh)
            })

    proposals.sort(key=lambda p: p["score"])
    assigned = [None] * len(items)
    used = []
    for proposal in proposals:
        index = proposal["itemIndex"]
        if assigned[index] is not None:
            continue
        cx, cy = proposal["center"]
        if any(math.hypot(cx - ux, cy - uy) < 8.0 for ux, uy in used):
            continue
        assigned[index] = proposal
        used.append((cx, cy))
    return assigned


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
        if distance > diagonal * 0.05:
            continue
        item = items[item_index]
        sx1, sy1, sx2, sy2 = _seed_rect(item, image_size, width, height)
        seed_area = max(1.0, (sx2 - sx1) * (sy2 - sy1))
        area_ratio = detections[detection_index]["area"] / seed_area
        if not 0.18 <= area_ratio <= 4.0:
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
    debug_mask = make_annotation_difference_mask(annotated, base)
    debug_mask_path = output_path.with_name("detected_label_frames_mask.png")
    debug_mask_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(debug_mask_path), debug_mask)
    matches = detect_seeded_label_quadrilaterals(
        annotated, seeds["items"], seeds["imageSize"], base.shape[1], base.shape[0],
        base=base
    )

    result_items = []
    preview = base.copy()
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
        "detectionMethod": "seeded_paired_image_difference_quadrilateral",
        "detectedShapeCount": matched_count,
        "differenceMaskPixelCount": int(np.count_nonzero(debug_mask)),
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
            for d in matches if d is not None
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
