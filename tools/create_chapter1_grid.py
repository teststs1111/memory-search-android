from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reference" / "chapter_01" / "base.jpg"
REF = ROOT / "reference" / "chapter_01"
OUTPUT = REF / "base_grid.jpg"
LEFT = REF / "left.jpg"
RIGHT = REF / "right.jpg"


def register_view(base, view, name: str):
    gray_base = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    gray_view = cv2.cvtColor(view, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(nfeatures=6000)
    key_base, desc_base = sift.detectAndCompute(gray_base, None)
    key_view, desc_view = sift.detectAndCompute(gray_view, None)
    if desc_base is None or desc_view is None:
        raise SystemExit(f"Not enough image features to register {name}")
    matcher = cv2.BFMatcher(cv2.NORM_L2)
    pairs = matcher.knnMatch(desc_view, desc_base, k=2)
    good = [m for m, n in pairs if m.distance < 0.72 * n.distance]
    if len(good) < 12:
        raise SystemExit(f"Not enough reliable matches for {name}: {len(good)}")
    src = np.float32([key_view[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([key_base[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    if matrix is None:
        raise SystemExit(f"Could not estimate transform for {name}")
    inliers = int(mask.sum())
    warped = cv2.warpPerspective(view, matrix, (base.shape[1], base.shape[0]))
    blended = cv2.addWeighted(base, 0.55, warped, 0.45, 0)
    cv2.imwrite(str(REF / f"{name}_registered_check.jpg"), blended,
                [cv2.IMWRITE_JPEG_QUALITY, 94])
    return len(good), inliers

def main() -> None:
    image = cv2.imread(str(SOURCE), cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f"Could not read {SOURCE}")
    height, width = image.shape[:2]
    overlay = image.copy()

    # Draw a normalized 0.05 grid. Coordinates refer to the original image,
    # with (0, 0) at the top-left and (1, 1) at the bottom-right.
    for step in range(21):
        x = round(step * (width - 1) / 20)
        y = round(step * (height - 1) / 20)
        cv2.line(overlay, (x, 0), (x, height - 1), (30, 210, 255), 1, cv2.LINE_AA)
        cv2.line(overlay, (0, y), (width - 1, y), (30, 210, 255), 1, cv2.LINE_AA)

        label = f"{step / 20:.2f}"
        cv2.putText(overlay, label, (min(x + 2, width - 38), 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(overlay, label, (2, min(y + 12, height - 2)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 0), 2, cv2.LINE_AA)

    result = cv2.addWeighted(overlay, 0.72, image, 0.28, 0)
    if not cv2.imwrite(str(OUTPUT), result, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise SystemExit(f"Could not write {OUTPUT}")
    print(f"Created {OUTPUT.relative_to(ROOT)} from {width}x{height} source.")
    report = []
    for name, path in (("left", LEFT), ("right", RIGHT)):
        view = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if view is None:
            raise SystemExit(f"Could not read {path}")
        good, inliers = register_view(image, view, name)
        report.append(f"{name}: {inliers}/{good} SIFT matches were RANSAC inliers")
    (REF / "registration_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__":
    main()

# Grid generation is diagnostic only; it never changes the app dataset.
