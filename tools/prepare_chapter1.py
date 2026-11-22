from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "chapter_01"
LEFT = REF / "left.jpg"
RIGHT = REF / "right.jpg"
OUTPUT = REF / "annotated_pair.jpg"

def main() -> None:
    left = cv2.imread(str(LEFT), cv2.IMREAD_COLOR)
    right = cv2.imread(str(RIGHT), cv2.IMREAD_COLOR)
    if left is None or right is None:
        raise SystemExit("Could not read both Chapter 1 annotated references.")
    if left.shape[:2] != right.shape[:2]:
        raise SystemExit(f"Unexpected image sizes: left={left.shape}, right={right.shape}")

    # Keep both original views intact. They are separate annotated views, so
    # arrange them side by side instead of pretending they form a seamless panorama.
    gap = 12
    canvas = np.full((left.shape[0], left.shape[1] + gap + right.shape[1], 3), 245, dtype=np.uint8)
    canvas[:, :left.shape[1]] = left
    canvas[:, left.shape[1] + gap:] = right

    if not cv2.imwrite(str(OUTPUT), canvas, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit("Could not write combined reference sheet.")
    print(f"Created {OUTPUT.relative_to(ROOT)} ({canvas.shape[1]}x{canvas.shape[0]}).")

if __name__ == "__main__":
    main()
