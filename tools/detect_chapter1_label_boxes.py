from pathlib import Path
import csv
import io
import json
import subprocess
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "chapter_01"
BASE_PATH = REF / "base.jpg"
VIEWS = [("left", REF / "left.jpg"), ("right", REF / "right.jpg")]
OUT_IMAGE = REF / "label_box_candidates.jpg"
OUT_JSON = REF / "label_box_candidates.json"


def ocr_text_lines(image_path):
    result = subprocess.run(
        ["tesseract", str(image_path), "stdout", "-l", "jpn", "--psm", "11", "tsv"],
        check=True, capture_output=True, text=True
    )
    rows = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
    grouped = {}
    for row in rows:
        text = (row.get("text") or "").strip()
        try:
            confidence = float(row.get("conf", "-1"))
        except ValueError:
            continue
        if not text or confidence < 10:
            continue
        key = (row["block_num"], row["par_num"], row["line_num"])
        x, y = int(row["left"]), int(row["top"])
        w, h = int(row["width"]), int(row["height"])
        if key not in grouped:
            grouped[key] = [x, y, x + w, y + h, [text], confidence]
        else:
            b = grouped[key]
            b[0], b[1] = min(b[0], x), min(b[1], y)
            b[2], b[3] = max(b[2], x + w), max(b[3], y + h)
            b[4].append(text)
            b[5] = max(b[5], confidence)
    lines = []
    for b in grouped.values():
        lines.append({"x1": b[0], "y1": b[1], "x2": b[2], "y2": b[3],
                      "text": "".join(b[4]), "confidence": round(b[5], 1)})
    return sorted(lines, key=lambda b: (b["y1"], b["x1"]))


def merge_label_lines(lines, image_shape):
    # Multi-line Japanese labels form compact text blocks. Merge only lines
    # with substantial horizontal overlap and a small vertical gap.
    groups = []
    for line in lines:
        x1, y1, x2, y2 = line["x1"], line["y1"], line["x2"], line["y2"]
        matches = []
        for i, g in enumerate(groups):
            gx1, gy1, gx2, gy2 = g["box"]
            overlap = max(0, min(x2, gx2) - max(x1, gx1))
            min_width = max(1, min(x2 - x1, gx2 - gx1))
            gap = max(0, max(y1, gy1) - min(y2, gy2))
            if overlap / min_width >= 0.28 and gap <= 15:
                matches.append(i)
        if not matches:
            groups.append({"box": [x1, y1, x2, y2], "texts": [line["text"]]})
        else:
            g = groups[matches[0]]
            g["box"] = [min(g["box"][0], x1), min(g["box"][1], y1),
                        max(g["box"][2], x2), max(g["box"][3], y2)]
            g["texts"].append(line["text"])
    h, w = image_shape[:2]
    boxes = []
    for g in groups:
        x1, y1, x2, y2 = g["box"]
        # Add padding to recover the dark label panel around the OCR glyphs.
        x1, y1 = max(0, x1 - 9), max(0, y1 - 6)
        x2, y2 = min(w - 1, x2 + 9), min(h - 1, y2 + 6)
        if x2 - x1 < 20 or y2 - y1 < 12:
            continue
        boxes.append((x1, y1, x2 - x1, y2 - y1, "".join(g["texts"])))
    return sorted(boxes, key=lambda b: (b[1], b[0]))


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

        lines = ocr_text_lines(path)
        boxes = merge_label_lines(lines, view.shape)
        for x, y, bw, bh, text in boxes:
            corners = np.float32([[[x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]]])
            mapped = cv2.perspectiveTransform(corners, matrix)[0]
            mapped[:, 0] = np.clip(mapped[:, 0], 0, width - 1)
            mapped[:, 1] = np.clip(mapped[:, 1], 0, height - 1)
            polygon = np.round(mapped).astype(np.int32)
            cv2.polylines(preview, [polygon], True, (0, 255, 255), 2, cv2.LINE_AA)
            center = tuple(np.mean(polygon, axis=0).astype(int))
            records.append({
                "source": view_name, "recognizedText": text,
                "sourceBox": [x, y, bw, bh], "basePolygon": polygon.tolist(),
                "confidence": "ocr_candidate_only"
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
        "note": "OCR text bounds padded to approximate annotation label panels, then transformed onto base.jpg. Not app runtime data.",
        "imageSize": [width, height], "boxes": records
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(records)} OCR label-box candidates; preview={OUT_IMAGE.name}")


if __name__ == "__main__":
    main()
