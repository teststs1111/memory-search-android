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

# Pixel-difference extraction identified the card regions. These bounds split
# touching cards at their visible edges and merge fragments belonging to one card.
# Coordinates are in the original 414x739 annotated source images.
PLATES = {
    "left": [
        ("マグカップ", (81, 280, 130, 316)),
        ("テディベア", (133, 271, 173, 310)),
        ("呼び出しボタン", (310, 175, 372, 211)),
        ("バーコードスキャナー", (285, 223, 360, 259)),
        ("いちごクッション", (45, 321, 114, 354)),
        ("卓上ベル", (168, 309, 235, 333)),
        ("カップケーキ", (268, 286, 321, 327)),
        ("おにぎり", (320, 304, 386, 328)),
        ("売り切れプレート", (353, 369, 414, 405)),
        ("トレー", (10, 439, 77, 466)),
        ("ロールケーキ", (229, 411, 317, 431)),
        ("マカロン", (353, 461, 414, 481)),
        ("ラッピングリボン", (129, 462, 199, 496)),
        ("いちごプリン", (25, 493, 78, 531)),
        ("アイリスメガネ", (79, 496, 145, 534)),
        ("黒いリボン", (0, 545, 81, 567)),
        ("ピンクのカゴ", (283, 572, 401, 600)),
        ("レシート", (34, 627, 100, 648)),
        ("ハンカチ", (132, 609, 198, 630)),
        ("いちごスプーン", (221, 606, 278, 639)),
        ("プリンのスタンプ", (157, 655, 215, 688)),
        ("ハートのティッシュ", (226, 644, 296, 677)),
        ("ポイントカード", (72, 665, 144, 706)),
        ("学生証", (319, 693, 386, 721)),
    ],
    "right": [
        ("プリンの張り紙", (130, 68, 247, 136)),
        ("プリンのぬいぐるみ", (145, 217, 239, 262)),
        ("コーヒー牛乳", (384, 141, 414, 260)),
        ("いちごオレ", (356, 145, 389, 257)),
        ("牛乳", (325, 169, 362, 247)),
        ("イチゴジャム", (333, 495, 412, 552)),
        ("ドーナツボックス", (307, 575, 397, 627)),
        ("ゴールドスプーン", (194, 672, 288, 726)),
    ],
}


def registration(source, base):
    sift = cv2.SIFT_create(nfeatures=8000)
    source_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)
    base_gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    source_kp, source_desc = sift.detectAndCompute(source_gray, None)
    base_kp, base_desc = sift.detectAndCompute(base_gray, None)
    if source_desc is None or base_desc is None:
        raise RuntimeError("Could not extract image features")
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(source_desc, base_desc, k=2)
    good = [m for m, n in pairs if m.distance < 0.72 * n.distance]
    src = np.float32([source_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([base_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    matrix, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    count = int(inliers.sum()) if inliers is not None else 0
    if matrix is None or count < 100:
        raise RuntimeError(f"Unreliable registration: {count}/{len(good)}")
    return matrix, {"matches": len(good), "inliers": count}


def main():
    base = cv2.imread(str(BASE_PATH))
    if base is None:
        raise SystemExit("base.jpg could not be loaded")
    height, width = base.shape[:2]
    preview = base.copy()
    records = []
    reports = {}

    for view_name, path in VIEWS:
        source = cv2.imread(str(path))
        if source is None or source.shape[:2] != base.shape[:2]:
            raise SystemExit(f"Invalid source image: {path.name}")
        matrix, report = registration(source, base)
        reports[view_name] = report

        for name, (x1, y1, x2, y2) in PLATES[view_name]:
            source_corners = np.float32([[
                [x1, y1], [x2, y1], [x2, y2], [x1, y2]
            ]])
            mapped = cv2.perspectiveTransform(source_corners, matrix)[0]
            mapped[:, 0] = np.clip(mapped[:, 0], 0, width - 1)
            mapped[:, 1] = np.clip(mapped[:, 1], 0, height - 1)
            polygon = np.round(mapped).astype(int)
            number = len(records) + 1
            cv2.polylines(preview, [polygon.reshape(-1, 1, 2)], True,
                          (0, 255, 255), 1, cv2.LINE_AA)
            center = tuple(np.mean(polygon, axis=0).astype(int))
            cv2.putText(preview, str(number), center, cv2.FONT_HERSHEY_SIMPLEX,
                        0.38, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(preview, str(number), center, cv2.FONT_HERSHEY_SIMPLEX,
                        0.38, (255, 255, 255), 1, cv2.LINE_AA)
            records.append({
                "number": number,
                "name": name,
                "source": view_name,
                "sourceRect": [x1, y1, x2, y2],
                "basePolygon": polygon.tolist(),
                "status": "candidate_from_pixel_difference_review",
            })

    if len(records) != 32:
        raise SystemExit(f"Expected 32 label cards, got {len(records)}")
    cv2.imwrite(str(OUT_IMAGE), preview, [cv2.IMWRITE_JPEG_QUALITY, 96])
    OUT_JSON.write_text(json.dumps({
        "status": "32_source_label_cards_mapped",
        "method": "Bounds were traced from the actual darkening regions in left.jpg/right.jpg, with touching panels split and duplicate fragments merged; SIFT/RANSAC maps each source quadrilateral onto base.jpg.",
        "reviewRequired": True,
        "registration": reports,
        "panelCount": len(records),
        "panels": records,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"registration": reports, "panelCount": len(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
