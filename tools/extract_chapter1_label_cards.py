from pathlib import Path
import json
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "chapter_01"
BASE_PATH = REF / "base.jpg"
VIEWS = [("left", REF / "left.jpg", 24), ("right", REF / "right.jpg", 8)]
OUT_IMAGE = REF / "label_box_candidates.jpg"
OUT_JSON = REF / "label_box_candidates.json"


def register_to_base(source, base):
    sift = cv2.SIFT_create(nfeatures=8000)
    source_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    base_gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    source_kp, source_desc = sift.detectAndCompute(source_gray, None)
    base_kp, base_desc = sift.detectAndCompute(base_gray, None)
    if source_desc is None or base_desc is None:
        raise RuntimeError("Could not extract image features")
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(source_desc, base_desc, k=2)
    good = [m for m, n in pairs if m.distance < 0.72 * n.distance]
    if len(good) < 40:
        raise RuntimeError(f"Too few registration matches: {len(good)}")
    src = np.float32([source_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([base_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    matrix, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    inlier_count = int(inliers.sum()) if inliers is not None else 0
    if matrix is None or inlier_count < 100:
        raise RuntimeError(f"Unreliable registration: {inlier_count}/{len(good)} inliers")
    return matrix, {"matches": len(good), "inliers": inlier_count}


def extract_dark_panels(source, base_in_source, view_name, threshold):
    source_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY).astype(np.float32)
    reference_gray = cv2.cvtColor(base_in_source, cv2.COLOR_BGR2GRAY).astype(np.float32)

    # Black translucent annotation plates reduce the underlying scene brightness.
    # A relative ratio catches the overlay even over dark objects and avoids
    # relying on a fixed absolute brightness difference.
    valid = reference_gray >= 24
    ratio = np.ones_like(source_gray, dtype=np.float32)
    ratio[valid] = (source_gray[valid] + 1.0) / (reference_gray[valid] + 1.0)
    mask = np.where(valid & (ratio < threshold), 255, 0).astype(np.uint8)

    # Only close one-pixel resampling gaps. Larger kernels merge neighboring labels.
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    )
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = mask.shape
    panels = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        if area < 35 or w < 8 or h < 8 or w > width * 0.40 or h > height * 0.18:
            continue
        if w / max(h, 1) > 8.0 or h / max(w, 1) > 8.0:
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, max(0.8, perimeter * 0.008), True)
        panels.append({
            "source": view_name,
            "area": round(float(area), 1),
            "sourceBounds": [int(x), int(y), int(x + w), int(y + h)],
            "sourcePolygon": polygon.reshape(-1, 2).astype(float).tolist(),
        })

    panels.sort(key=lambda p: (p["sourceBounds"][1] // 10, p["sourceBounds"][0]))
    return panels, mask


def main():
    base = cv2.imread(str(BASE_PATH))
    if base is None:
        raise SystemExit("base.jpg could not be loaded")

    preview = base.copy()
    all_panels = []
    reports = {}

    for view_name, path, expected in VIEWS:
        source = cv2.imread(str(path))
        if source is None:
            raise SystemExit(f"{path.name} could not be loaded")
        if source.shape[:2] != base.shape[:2]:
            raise SystemExit(f"{path.name} and base.jpg dimensions differ")

        matrix, registration = register_to_base(source, base)
        inverse = np.linalg.inv(matrix)
        height, width = source.shape[:2]
        base_in_source = cv2.warpPerspective(
            base, inverse, (width, height), flags=cv2.INTER_LINEAR
        )
        sweep = {}
        for threshold in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
            test_panels, _ = extract_dark_panels(source, base_in_source, view_name, threshold)
            sweep[str(threshold)] = len(test_panels)

        panels, mask = extract_dark_panels(source, base_in_source, view_name, 0.45)
        cv2.imwrite(str(REF / f"{view_name}_annotation_diff_mask.png"), mask)

        reports[view_name] = {
            **registration,
            "expectedPanels": expected,
            "detectedPanels": len(panels),
            "thresholdSweep": sweep,
        }
        for panel in panels:
            source_poly = np.asarray(panel["sourcePolygon"], dtype=np.float32).reshape(-1, 1, 2)
            mapped = cv2.perspectiveTransform(source_poly, matrix).reshape(-1, 2)
            mapped[:, 0] = np.clip(mapped[:, 0], 0, base.shape[1] - 1)
            mapped[:, 1] = np.clip(mapped[:, 1], 0, base.shape[0] - 1)
            polygon = np.round(mapped).astype(int).tolist()
            panel["polygon"] = polygon
            panel["bounds"] = [
                int(np.min(mapped[:, 0])), int(np.min(mapped[:, 1])),
                int(np.max(mapped[:, 0])), int(np.max(mapped[:, 1])),
            ]
            panel["number"] = len(all_panels) + 1
            all_panels.append(panel)

            poly = np.asarray(polygon, dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(preview, [poly], True, (0, 255, 255), 1, cv2.LINE_AA)
            x1, y1, _, _ = panel["bounds"]
            cv2.putText(preview, str(panel["number"]), (x1, max(10, y1 - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(preview, str(panel["number"]), (x1, max(10, y1 - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imwrite(str(OUT_IMAGE), preview, [cv2.IMWRITE_JPEG_QUALITY, 96])
    OUT_JSON.write_text(json.dumps({
        "status": "image_difference_extraction_candidates",
        "method": "Register base into each annotated source image; detect pixels darkened by the translucent black name plates using relative luminance; trace contours in source coordinates and transform them to base.",
        "reviewRequired": True,
        "reports": reports,
        "panelCount": len(all_panels),
        "panels": all_panels,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False))
    print(f"Detected {len(all_panels)} candidate panels; expected 32")


if __name__ == "__main__":
    main()
