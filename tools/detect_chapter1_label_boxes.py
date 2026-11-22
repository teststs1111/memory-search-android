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

# Hand-marked outer bounds of the dark name plates in the submitted annotated
# images. Coordinates are in the original 414x739 reference-image space.
# These are explicit source rectangles; no OCR or dark-region detection.
PLATES = {
    "left": [
        ("マグカップ", (78, 278, 130, 313)),
        ("テディベア", (130, 269, 172, 310)),
        ("呼び出しボタン", (307, 174, 372, 212)),
        ("バーコードスキャナー", (283, 221, 359, 255)),
        ("いちごクッション", (42, 319, 104, 354)),
        ("卓上ベル", (167, 309, 236, 334)),
        ("カップケーキ", (263, 285, 319, 324)),
        ("おにぎり", (323, 304, 375, 327)),
        ("売り切れプレート", (350, 371, 412, 405)),
        ("トレー", (6, 436, 46, 467)),
        ("ロールケーキ", (227, 409, 294, 433)),
        ("マカロン", (350, 458, 407, 484)),
        ("ラッピングリボン", (130, 465, 192, 499)),
        ("いちごプリン", (24, 490, 78, 531)),
        ("アイリスメガネ", (82, 495, 146, 532)),
        ("黒いリボン", (0, 544, 76, 571)),
        ("ピンクのカゴ", (281, 568, 378, 605)),
        ("レシート", (31, 623, 103, 651)),
        ("ハンカチ", (129, 604, 200, 635)),
        ("いちごスプーン", (216, 635, 279, 679)),
        ("プリンのスタンプ", (153, 653, 218, 691)),
        ("ハートのティッシュ", (226, 642, 298, 681)),
        ("ポイントカード", (70, 666, 135, 713)),
        ("学生証", (315, 697, 374, 732)),
    ],
    "right": [
        ("プリンの張り紙", (128, 67, 244, 137)),
        ("プリンのぬいぐるみ", (143, 220, 235, 261)),
        ("コーヒー牛乳", (337, 111, 411, 151)),
        ("いちごオレ", (362, 145, 411, 194)),
        ("牛乳", (330, 126, 372, 197)),
        ("イチゴジャム", (335, 430, 405, 505)),
        ("ドーナツボックス", (302, 514, 374, 568)),
        ("ゴールドスプーン", (197, 670, 291, 731)),
    ],
}


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
        vh, vw = view.shape[:2]
        if (vw, vh) != (414, 739):
            raise SystemExit(f"Unexpected {view_name}.jpg dimensions: {vw}x{vh}")
        gray = cv2.cvtColor(view, cv2.COLOR_BGR2GRAY)
        kp, desc = sift.detectAndCompute(gray, None)
        pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(desc, base_desc, k=2)
        good = [m for m, n in pairs if m.distance < 0.72 * n.distance]
        src = np.float32([kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([base_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        matrix, inlier_mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
        if matrix is None or int(inlier_mask.sum()) < 30:
            raise SystemExit(f"Unreliable image registration for {view_name}")

        for name, (x1, y1, x2, y2) in PLATES[view_name]:
            corners = np.float32([[[x1, y1], [x2, y1], [x2, y2], [x1, y2]]])
            mapped = cv2.perspectiveTransform(corners, matrix)[0]
            mapped[:, 0] = np.clip(mapped[:, 0], 0, width - 1)
            mapped[:, 1] = np.clip(mapped[:, 1], 0, height - 1)
            polygon = np.round(mapped).astype(np.int32)
            cv2.polylines(preview, [polygon], True, (0, 255, 255), 1, cv2.LINE_AA)
            records.append({
                "number": len(records) + 1,
                "name": name,
                "source": view_name,
                "sourceRect": [x1, y1, x2, y2],
                "basePolygon": polygon.tolist(),
                "confidence": "manual_source_plate_bounds_needs_visual_review"
            })

    for record in records:
        poly = np.array(record["basePolygon"], dtype=np.int32)
        center = tuple(np.mean(poly, axis=0).astype(int))
        label = str(record["number"])
        cv2.putText(preview, label, center, cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(preview, label, center, cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (255, 255, 255), 1, cv2.LINE_AA)

    if len(records) != 32:
        raise SystemExit(f"Expected 32 manually defined plates, got {len(records)}")
    if not cv2.imwrite(str(OUT_IMAGE), preview, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise SystemExit("Could not write preview")
    OUT_JSON.write_text(json.dumps({
        "status": "manual_source_rect_candidates",
        "note": "32 individually specified outer name-plate rectangles from submitted left.jpg/right.jpg, transformed onto base.jpg. Approximate hand-marked bounds; review required; not app runtime data.",
        "imageSize": [width, height],
        "panelCount": len(records),
        "panels": records
    }, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(f"Created {len(records)} manually specified plate candidates")


if __name__ == "__main__":
    main()
