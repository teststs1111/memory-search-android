from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference" / "chapter_01"
LEFT = REF / "left.jpg"
RIGHT = REF / "right.jpg"
OUTPUT = REF / "annotated_combined.jpg"

def main() -> None:
    left = cv2.imread(str(LEFT), cv2.IMREAD_COLOR)
    right = cv2.imread(str(RIGHT), cv2.IMREAD_COLOR)
    if left is None or right is None:
        raise SystemExit("Could not read both Chapter 1 annotated references.")
    if left.shape[:2] != right.shape[:2]:
        raise SystemExit(f"Unexpected image sizes: left={left.shape}, right={right.shape}")

    stitcher = cv2.Stitcher_create(cv2.Stitcher_PANORAMA)
    status, panorama = stitcher.stitch([left, right])
    if status != cv2.Stitcher_OK or panorama is None:
        raise SystemExit(f"OpenCV stitching failed with status {status}; originals were left untouched.")

    height, width = panorama.shape[:2]
    if width <= left.shape[1] or height < int(left.shape[0] * 0.65):
        raise SystemExit(f"Stitched result does not look like a horizontal panorama: {width}x{height}")

    if not cv2.imwrite(str(OUTPUT), panorama, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit("Could not write combined reference image.")
    print(f"Created {OUTPUT.relative_to(ROOT)} ({width}x{height}).")

if __name__ == "__main__":
    main()
