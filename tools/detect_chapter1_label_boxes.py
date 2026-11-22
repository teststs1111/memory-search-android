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


def find_label_boxes(image, name):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    # The annotation labels are translucent charcoal rectangles with white text.
    mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 105, 112]))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 7))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(closed, 8)
    boxes = []
    h, w = image.shape[:2]
    for i in range(1, count):
        x, y, bw, bh, area = map(int, stats[i])
        if bw < 22 or bh < 13 or area < 250:
            continue
        ratio = bw / max(bh, 1)
        if ratio > 9.0 or ratio < 0.55 or bw > w * 0.48 or bh > h * 0.16:
            continue
        # Keep compact label-like regions; reject large scene shadows and furniture.
        fill = area / float(bw * bh)
        if fill < 0.30:
            continue
        boxes.append((x, y, bw, bh, round(fill, 3)))
    boxes.sort(key=lambda b: (b[1], b[0]))
    return boxes


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

        boxes = find_label_boxes(view, view_name)
        for x, y, bw, bh, fill in boxes:
            corners = np.float32([[[x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]]])
            mapped = cv2.perspectiveTransform(corners, matrix)[0]
            mapped[:, 0] = np.clip(mapped[:, 0], 0, width - 1)
            mapped[:, 1] = np.clip(mapped[:, 1], 0, height - 1)
            polygon = np.round(mapped).astype(np.int32)
            cv2.polylines(preview, [polygon], True, (0, 255, 255), 2, cv2.LINE_AA)
            center = tuple(np.mean(polygon, axis=0).astype(int))
            records.append({
                "source": view_name,
                "sourceBox": [x, y, bw, bh],
                "basePolygon": polygon.tolist(),
                "center": [round(float(np.mean(mapped[:, 0])) / (width - 1), 6),
                           round(float(np.mean(mapped[:, 1])) / (height - 1), 6)],
                "fillRatio": fill
            })
    for i, record in enumerate(records, 1):
        poly = np.array(record["basePolygon"], dtype=np.int32)
        c = tuple(np.mean(poly, axis=0).astype(int))
        cv2.putText(preview, str(i), (c[0], c[1]), cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(preview, str(i), (c[0], c[1]), cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, (255, 255, 255), 1, cv2.LINE_AA)
    if not cv2.imwrite(str(OUT_IMAGE), preview, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise SystemExit("Could not write label_box_candidates.jpg")
    OUT_JSON.write_text(json.dumps({
        "status": "visual_candidates_only",
        "note": "Detected annotation label rectangles transformed onto base.jpg. Not app runtime data; text-to-item mapping and visual verification remain pending.",
        "imageSize": [width, height],
        "boxes": records
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Detected {len(records)} candidate label rectangles; preview={OUT_IMAGE.name}")


if __name__ == "__main__":
    main()
