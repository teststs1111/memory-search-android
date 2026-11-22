from pathlib import Path
import json
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "chapter_01"
BASE_PATH = REF / "base.jpg"
VIEWS = [("left", REF / "left.jpg"), ("right", REF / "right.jpg")]
OUT_IMAGE = REF / "label_box_candidates.jpg"
OUT_JSON = REF / "label_box_candidates.json"


def detect_dark_label_panels(image):
    """Detect the dark rectangular name plates themselves, not the OCR text."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # The supplied annotation plates are dark and nearly neutral. White text
    # is excluded; closing bridges small letter-shaped gaps in each plate.
    mask = cv2.inRange(hsv, np.array([0, 0, 18]), np.array([180, 115, 128]))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (19, 13))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    image_h, image_w = image.shape[:2]
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if w < 25 or h < 14 or w > image_w * 0.62 or h > image_h * 0.20:
            continue
        ratio = w / float(h)
        if ratio < 0.38 or ratio > 6.5:
            continue
        rectangularity = area / float(w * h)
        if rectangularity < 0.22:
            continue
        # Require a substantial dark fill inside the bounding rectangle.
        roi = mask[y:y+h, x:x+w]
        fill = cv2.countNonZero(roi) / float(w * h)
        if fill < 0.20:
            continue
        # Ignore large scene objects by requiring a compact, plate-like shape.
        approx = cv2.approxPolyDP(contour, 0.035 * cv2.arcLength(contour, True), True)
        if len(approx) < 4 or len(approx) > 12:
            continue
        candidates.append((x, y, w, h, round(fill, 3), round(rectangularity, 3)))

    # Remove nested/near-duplicate detections; retain the larger outer plate.
    candidates.sort(key=lambda b: b[2] * b[3], reverse=True)
    kept = []
    for candidate in candidates:
        x, y, w, h = candidate[:4]
        cx, cy = x + w / 2, y + h / 2
        duplicate = False
        for other in kept:
            ox, oy, ow, oh = other[:4]
            if ox <= cx <= ox + ow and oy <= cy <= oy + oh:
                duplicate = True
                break
        if not duplicate:
            kept.append(candidate)
    return sorted(kept, key=lambda b: (b[1], b[0]))


def main():
    base = cv2.imread(str(BASE_PATH))
    if base is None:
        raise SystemExit("base.jpg could not be loaded")
    height, width = base.shape[:2]
    sift = cv2.SIFT_create(nfeatures=6000)
    base_gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    base_kp, base_desc = sift.detectAndCompute(base_gray, None)
    if base_desc is None:
        raise SystemExit("No features found in base image")

    preview = base.copy()
    records = []
    for view_name, path in VIEWS:
        view = cv2.imread(str(path))
        if view is None:
            raise SystemExit(f"{path.name} could not be loaded")
        gray = cv2.cvtColor(view, cv2.COLOR_BGR2GRAY)
        kp, desc = sift.detectAndCompute(gray, None)
        pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(desc, base_desc, k=2)
        good = [m for m, n in pairs if m.distance < 0.72 * n.distance]
        src = np.float32([kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([base_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        matrix, inlier_mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
        if matrix is None or int(inlier_mask.sum()) < 30:
            raise SystemExit(f"Unreliable image registration for {view_name}")

        panels = detect_dark_label_panels(view)
        for x, y, bw, bh, fill, rectangularity in panels:
            corners = np.float32([[[x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]]])
            mapped = cv2.perspectiveTransform(corners, matrix)[0]
            mapped[:, 0] = np.clip(mapped[:, 0], 0, width - 1)
            mapped[:, 1] = np.clip(mapped[:, 1], 0, height - 1)
            polygon = np.round(mapped).astype(np.int32)
            cv2.polylines(preview, [polygon], True, (0, 255, 255), 1, cv2.LINE_AA)
            records.append({
                "source": view_name,
                "sourcePanelRect": [x, y, bw, bh],
                "basePolygon": polygon.tolist(),
                "darkFillRatio": fill,
                "rectangularity": rectangularity,
                "confidence": "panel_contour_candidate_only"
            })

    for i, record in enumerate(records, 1):
        poly = np.array(record["basePolygon"], dtype=np.int32)
        c = tuple(np.mean(poly, axis=0).astype(int))
        cv2.putText(preview, str(i), (c[0], c[1]), cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(preview, str(i), (c[0], c[1]), cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, (255, 255, 255), 1, cv2.LINE_AA)

    if not records:
        raise SystemExit("No dark label panels detected; refusing to publish an empty preview")
    if not cv2.imwrite(str(OUT_IMAGE), preview, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise SystemExit("Could not write label_box_candidates.jpg")
    OUT_JSON.write_text(json.dumps({
        "status": "visual_candidates_only",
        "note": "Detected connected dark annotation panel regions with larger morphological closing (not OCR text bounds), then mapped the panel outer rectangles onto base.jpg. Review required; not app runtime data.",
        "imageSize": [width, height],
        "panelCount": len(records),
        "panels": records
    }, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(f"Created {len(records)} dark panel candidates; preview={OUT_IMAGE.name}")


if __name__ == "__main__":
    main()
