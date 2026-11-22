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
    height, width = base.shape[:2]
    warped = cv2.warpPerspective(source, matrix, (width, height), flags=cv2.INTER_LINEAR)
    return warped, {"matches": len(good), "inliers": inlier_count}


def extract_dark_panels(base, warped, expected, view_name):
    base_gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY).astype(np.int16)
    warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY).astype(np.int16)

    # The annotation cards darken the original scene. White lettering brightens
    # pixels, so only positive luminance loss is used as the panel mask.
    darkening = np.maximum(base_gray - warped_gray, 0).astype(np.uint8)
    mask = np.where(darkening >= 22, 255, 0).astype(np.uint8)

    # Bridge tiny gaps caused by white glyphs and image resampling. External
    # contours then recover each dark card's outer boundary, not text bounds.
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    )
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    )

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = mask.shape
    panels = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        if area < 55 or w < 9 or h < 9 or w > width * 0.42 or h > height * 0.20:
            continue
        # Ignore large registration artifacts and thin isolated text strokes.
        if w / max(h, 1) > 7.5 or h / max(w, 1) > 7.5:
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, max(1.0, perimeter * 0.012), True)
        panels.append({
            "source": view_name,
            "area": round(float(area), 1),
            "bounds": [int(x), int(y), int(x + w), int(y + h)],
            "polygon": polygon.reshape(-1, 2).astype(int).tolist(),
        })

    # Stable visual reading order for review.
    panels.sort(key=lambda p: (p["bounds"][1] // 12, p["bounds"][0]))
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

        warped, registration = register_to_base(source, base)
        panels, mask = extract_dark_panels(base, warped, expected, view_name)
        cv2.imwrite(str(REF / f"{view_name}_annotation_diff_mask.png"), mask)
        reports[view_name] = {
            **registration,
            "expectedPanels": expected,
            "detectedPanels": len(panels),
        }
        for panel in panels:
            panel["number"] = len(all_panels) + 1
            all_panels.append(panel)
            poly = np.asarray(panel["polygon"], dtype=np.int32).reshape(-1, 1, 2)
            cv2.polylines(preview, [poly], True, (0, 255, 255), 1, cv2.LINE_AA)
            x1, y1, x2, y2 = panel["bounds"]
            cv2.putText(preview, str(panel["number"]), (x1, max(10, y1 - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(preview, str(panel["number"]), (x1, max(10, y1 - 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (255, 255, 255), 1, cv2.LINE_AA)

    cv2.imwrite(str(OUT_IMAGE), preview, [cv2.IMWRITE_JPEG_QUALITY, 96])
    OUT_JSON.write_text(json.dumps({
        "status": "image_difference_extraction_candidates",
        "method": "SIFT/RANSAC registration followed by source-vs-base luminance-difference masks; contours are extracted from the dark annotation cards.",
        "reviewRequired": True,
        "reports": reports,
        "panelCount": len(all_panels),
        "panels": all_panels,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(reports, ensure_ascii=False))
    print(f"Detected {len(all_panels)} candidate panels; expected 32")


if __name__ == "__main__":
    main()
