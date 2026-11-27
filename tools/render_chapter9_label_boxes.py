#!/usr/bin/env python3
"""Render and validate Chapter 9 review-only candidates against the original image pair."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "reference" / "chapter_09"
DATASET = ROOT / "app" / "src" / "main" / "assets" / "stages" / "chapter_9_label_boxes.candidates.json"
RUNTIME_DATASET = ROOT / "app" / "src" / "main" / "assets" / "stages" / "chapter_9.json"
CATALOG = ROOT / "app" / "src" / "main" / "assets" / "stages" / "item_catalogs.json"
BASE_IMAGE = CHAPTER_DIR / "base.jpg"
ANNOTATED_IMAGE = CHAPTER_DIR / "annotated.jpg"
OUTPUT = CHAPTER_DIR / "label_box_candidates.jpg"
COMPARISON = CHAPTER_DIR / "label_box_comparison.jpg"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_alignment(annotated: np.ndarray, base: np.ndarray):
    sift = cv2.SIFT_create(nfeatures=8000)
    keypoints_a, descriptors_a = sift.detectAndCompute(
        cv2.cvtColor(annotated, cv2.COLOR_BGR2GRAY), None
    )
    keypoints_b, descriptors_b = sift.detectAndCompute(
        cv2.cvtColor(base, cv2.COLOR_BGR2GRAY), None
    )
    if descriptors_a is None or descriptors_b is None:
        raise SystemExit("Could not extract enough reference-image features")
    pairs = cv2.BFMatcher().knnMatch(descriptors_a, descriptors_b, k=2)
    good = [first for first, second in pairs if first.distance < 0.72 * second.distance]
    if len(good) < 100:
        raise SystemExit(f"Insufficient image matches: {len(good)}")
    points_a = np.float32([keypoints_a[m.queryIdx].pt for m in good])
    points_b = np.float32([keypoints_b[m.trainIdx].pt for m in good])
    matrix, inlier_mask = cv2.findHomography(points_a, points_b, cv2.RANSAC, 3.0)
    if matrix is None or inlier_mask is None:
        raise SystemExit("Could not align annotated and clean reference images")
    inliers = int(inlier_mask.sum())
    ratio = inliers / len(good)
    if inliers < 500 or ratio < 0.70:
        raise SystemExit(
            f"Weak reference alignment: {inliers}/{len(good)} inliers ({ratio:.3f})"
        )
    return matrix, len(good), inliers, ratio


def mapped_basis_rect(rect: list[int], matrix: np.ndarray, base_shape: tuple[int, ...], basis: dict):
    x1, y1, x2, y2 = rect
    corners = np.float32([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]).reshape(-1, 1, 2)
    mapped = cv2.perspectiveTransform(corners, matrix).reshape(-1, 2)
    height, width = base_shape[:2]
    return [
        float(mapped[:, 0].min() / width * basis["width"]),
        float(mapped[:, 1].min() / height * basis["height"]),
        float(mapped[:, 0].max() / width * basis["width"]),
        float(mapped[:, 1].max() / height * basis["height"]),
    ]


def validate_candidate_data(data: dict, runtime: dict, catalog: dict, annotated: np.ndarray, base: np.ndarray):
    if data.get("runtimeEnabled") is not False:
        raise SystemExit("Chapter 9 candidate data must remain runtime-disabled")
    if data.get("dataStatus") != "partially_reviewed_candidate_only":
        raise SystemExit("Chapter 9 candidate data must remain review-only")
    if runtime.get("dataStatus") != "awaiting_coordinate_verification" or runtime.get("items") != []:
        raise SystemExit("Chapter 9 runtime dataset must remain pending and empty")

    height, width = base.shape[:2]
    annotated_height, annotated_width = annotated.shape[:2]
    if (width, height) != (
        data["actualReferenceImageSize"]["width"],
        data["actualReferenceImageSize"]["height"],
    ):
        raise SystemExit("Clean base dimensions do not match candidate provenance")
    if (annotated_width, annotated_height) != (
        data["actualAnnotatedImageSize"]["width"],
        data["actualAnnotatedImageSize"]["height"],
    ):
        raise SystemExit("Annotated source dimensions do not match candidate provenance")

    hashes = data["sourceImage"]
    if sha256(ANNOTATED_IMAGE) != hashes["annotatedSha256"]:
        raise SystemExit("Annotated source SHA-256 does not match candidate provenance")
    if sha256(BASE_IMAGE) != hashes["baseSha256"]:
        raise SystemExit("Clean base SHA-256 does not match candidate provenance")

    basis = data["imageSize"]
    catalog_names = next(
        chapter["itemNames"] for chapter in catalog["chapters"]
        if chapter["stageId"] == data["stageId"]
    )
    items = data["items"]
    if [item["itemName"] for item in items] != catalog_names:
        raise SystemExit("Candidate item order/names do not match the Chapter 9 catalog")
    ids = [item["itemId"] for item in items]
    if len(ids) != len(set(ids)):
        raise SystemExit("Candidate item IDs are not unique")

    matrix, good_count, inlier_count, ratio = compute_alignment(annotated, base)
    expected_matrix = np.asarray(data["referenceImageAlignment"]["annotatedToBaseHomography"])
    if np.max(np.abs(matrix - expected_matrix)) > 0.005:
        raise SystemExit("Recomputed source alignment differs from recorded homography")
    if good_count < 100 or inlier_count < 500 or ratio < 0.70:
        raise SystemExit("Source alignment quality is below the review threshold")

    for item in items:
        rect = item.get("sourceRect")
        bounds = item.get("bounds")
        annotated_rect = item.get("annotatedSourceRect")
        if rect is None:
            if bounds is not None or annotated_rect is not None:
                raise SystemExit(f"{item['itemName']}: missing candidate must not have bounds")
            if item.get("visualReviewStatus") != "missing_annotated_label":
                raise SystemExit(f"{item['itemName']}: missing candidate status is inconsistent")
            continue
        x1, y1, x2, y2 = rect
        if not (0 <= x1 < x2 <= basis["width"] and 0 <= y1 < y2 <= basis["height"]):
            raise SystemExit(f"{item['itemName']}: sourceRect is outside the 563x1000 basis")
        expected_bounds = {
            "left": x1 / basis["width"],
            "top": y1 / basis["height"],
            "right": x2 / basis["width"],
            "bottom": y2 / basis["height"],
        }
        for key, value in expected_bounds.items():
            if abs(bounds[key] - value) > 1e-6:
                raise SystemExit(f"{item['itemName']}: {key} does not match sourceRect")
        if annotated_rect is None:
            raise SystemExit(f"{item['itemName']}: candidate is missing its annotation source rect")
        mapped = mapped_basis_rect(annotated_rect, matrix, base.shape, basis)
        visible = [x1, y1, x2, y2]
        max_error = max(abs(mapped[index] - visible[index]) for index in range(4))
        if max_error > 4.0:
            raise SystemExit(
                f"{item['itemName']}: annotation-to-base mapping differs by {max_error:.2f} basis px"
            )
        if item.get("status") != "candidate_needs_visual_review":
            raise SystemExit(f"{item['itemName']}: matched candidate has unexpected status")

    review = data["visualReview"]
    if review["edgeClippedCandidateCount"] != len(review["edgeClippedItemNames"]):
        raise SystemExit("Edge-clipped candidate count is inconsistent")
    if review["nearEdgeCandidateCount"] != len(review["nearEdgeItemNames"]):
        raise SystemExit("Near-edge candidate count is inconsistent")
    if review["missingCatalogItemNames"] != ["ランチ"]:
        raise SystemExit("Chapter 9 missing catalog label discrepancy changed")
    if {entry["itemName"] for entry in review["unmatchedAnnotatedLabels"]} != {"救急箱", "ハサミ"}:
        raise SystemExit("Chapter 9 unmatched annotation labels changed")

    overlaps = []
    for index, first in enumerate(items):
        a = first.get("bounds")
        if a is None:
            continue
        for second in items[index + 1:]:
            b = second.get("bounds")
            if b is None:
                continue
            overlap_width = max(0.0, min(a["right"], b["right"]) - max(a["left"], b["left"]))
            overlap_height = max(0.0, min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]))
            if overlap_width * overlap_height > 0:
                overlaps.append([first["itemName"], second["itemName"]])
    if overlaps != review["overlappingCandidatePairs"]:
        raise SystemExit("Recorded Chapter 9 AABB overlaps do not match candidate geometry")
    if review.get("detectorOutputUsedAsCoordinateSource") is not False:
        raise SystemExit("Detector output must not be used as the coordinate source")
    return matrix, good_count, inlier_count, ratio


def draw_annotated(image: np.ndarray, items: list[dict], extras: list[dict]) -> np.ndarray:
    rendered = image.copy()
    for index, item in enumerate(items, start=1):
        rect = item.get("annotatedSourceRect")
        if rect is None:
            continue
        x1, y1, x2, y2 = rect
        status = item.get("visualReviewStatus")
        color = (0, 165, 255) if status in {
            "edge_clipped_pending_full_bounds", "near_edge_alignment_pending"
        } else (0, 220, 40)
        cv2.rectangle(rendered, (x1, y1), (x2, y2), color, 4, cv2.LINE_AA)
        marker_x = min(max(x1 + 15, 15), image.shape[1] - 16)
        marker_y = min(max(y1 + 15, 15), image.shape[0] - 16)
        cv2.circle(rendered, (marker_x, marker_y), 14, (20, 20, 20), -1, cv2.LINE_AA)
        cv2.putText(rendered, str(index), (marker_x - 5, marker_y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    for extra in extras:
        x1, y1, x2, y2 = extra["annotatedSourceRect"]
        cv2.rectangle(rendered, (x1, y1), (x2, y2), (0, 0, 255), 4, cv2.LINE_AA)
    return rendered


def draw_clean(image: np.ndarray, items: list[dict]) -> np.ndarray:
    height, width = image.shape[:2]
    rendered = image.copy()
    for index, item in enumerate(items, start=1):
        bounds = item.get("bounds")
        if bounds is None:
            continue
        x1 = max(0, min(width - 1, round(bounds["left"] * (width - 1))))
        y1 = max(0, min(height - 1, round(bounds["top"] * (height - 1))))
        x2 = max(0, min(width - 1, round(bounds["right"] * (width - 1))))
        y2 = max(0, min(height - 1, round(bounds["bottom"] * (height - 1))))
        status = item.get("visualReviewStatus")
        color = (0, 165, 255) if status in {
            "edge_clipped_pending_full_bounds", "near_edge_alignment_pending"
        } else (0, 220, 40)
        cv2.rectangle(rendered, (x1, y1), (x2, y2), color, 4, cv2.LINE_AA)
        marker_x = min(max(x1 + 15, 15), width - 16)
        marker_y = min(max(y1 + 15, 15), height - 16)
        cv2.circle(rendered, (marker_x, marker_y), 14, (20, 20, 20), -1, cv2.LINE_AA)
        cv2.putText(rendered, str(index), (marker_x - 5, marker_y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    return rendered


def main() -> None:
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    runtime = json.loads(RUNTIME_DATASET.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    base = cv2.imread(str(BASE_IMAGE), cv2.IMREAD_COLOR)
    annotated = cv2.imread(str(ANNOTATED_IMAGE), cv2.IMREAD_COLOR)
    if base is None or annotated is None:
        raise SystemExit("Could not read both Chapter 9 original reference images")

    matrix, good_count, inlier_count, ratio = validate_candidate_data(
        data, runtime, catalog, annotated, base
    )
    annotated_overlay = draw_annotated(
        annotated, data["items"], data["visualReview"]["unmatchedAnnotatedLabels"]
    )
    base_overlay = draw_clean(base, data["items"])
    if not cv2.imwrite(str(OUTPUT), base_overlay, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise SystemExit("Could not write clean-base candidate preview")

    gap = 24
    header_height = 82
    height = max(annotated_overlay.shape[0], base_overlay.shape[0])
    width = annotated_overlay.shape[1] + gap + base_overlay.shape[1]
    canvas = np.full((height + header_height, width, 3), 245, dtype=np.uint8)
    canvas[header_height:header_height + annotated_overlay.shape[0], :annotated_overlay.shape[1]] = annotated_overlay
    x_base = annotated_overlay.shape[1] + gap
    canvas[header_height:header_height + base_overlay.shape[0], x_base:x_base + base_overlay.shape[1]] = base_overlay
    cv2.putText(canvas, "ANNOTATED SOURCE + TRACED BOXES", (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (25, 25, 25), 2, cv2.LINE_AA)
    cv2.putText(canvas, "CLEAN BASE + MAPPED BOXES", (x_base + 12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, (25, 25, 25), 2, cv2.LINE_AA)
    cv2.putText(canvas, "28 complete / 3 edge-pending / 2 near-edge / 1 missing / 2 unmatched extras",
                (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (35, 35, 35), 1, cv2.LINE_AA)
    cv2.putText(canvas, f"SIFT/RANSAC alignment: {inlier_count}/{good_count} inliers ({ratio:.3f})",
                (12, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (50, 50, 50), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(COMPARISON), canvas, [cv2.IMWRITE_JPEG_QUALITY, 93]):
        raise SystemExit("Could not write annotated/base comparison")

    print(
        f"Rendered {len(data['items'])} Chapter 9 catalog entries; "
        f"28 complete, 3 edge-pending, 2 near-edge, 1 missing; "
        f"2 unmatched annotation labels and {len(data['visualReview']['overlappingCandidatePairs'])} AABB overlaps recorded. "
        f"Alignment {inlier_count}/{good_count} inliers ({ratio:.3f})."
    )


if __name__ == "__main__":
    main()
