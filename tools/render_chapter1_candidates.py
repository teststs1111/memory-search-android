import json
from pathlib import Path
import cv2

root = Path(__file__).resolve().parents[1]
folder = root / "reference" / "chapter_01"
data = json.loads((folder / "chapter_1_candidates.json").read_text(encoding="utf-8"))
image = cv2.imread(str(folder / "base.jpg"))
if image is None:
    raise SystemExit("base.jpg could not be loaded")
h, w = image.shape[:2]
for index, item in enumerate(data["items"], 1):
    x = round(item["x"] * (w - 1))
    y = round(item["y"] * (h - 1))
    cv2.circle(image, (x, y), 9, (0, 0, 255), 2, cv2.LINE_AA)
    cv2.circle(image, (x, y), 2, (0, 0, 255), -1, cv2.LINE_AA)
    label = str(index)
    px, py = min(x + 8, w - 18), max(y - 8, 14)
    cv2.putText(image, label, (px, py), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(image, label, (px, py), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                (255, 255, 255), 1, cv2.LINE_AA)
out = folder / "candidate_markers.jpg"
if not cv2.imwrite(str(out), image, [cv2.IMWRITE_JPEG_QUALITY, 94]):
    raise SystemExit("Could not write candidate_markers.jpg")
print(f"Created {out.relative_to(root)} with {len(data['items'])} provisional markers.")
