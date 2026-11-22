from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reference" / "chapter_01" / "base.jpg"
OUTPUT = ROOT / "reference" / "chapter_01" / "base_grid.jpg"

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

if __name__ == "__main__":
    main()
