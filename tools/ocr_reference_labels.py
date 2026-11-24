#!/usr/bin/env python3
"""Extract Japanese text line positions from annotated reference images.

This is a diagnostic stage only: OCR boxes are anchors for locating labels,
not substitutes for the translucent label-frame boundaries.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import cv2


def normalize(text: str) -> str:
    return re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠ー]", "", text).lower()


def run_tesseract(image_path: Path, scale: int = 3) -> list[dict]:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")
    height, width = image.shape[:2]
    enlarged = cv2.resize(image, (width * scale, height * scale), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(enlarged, cv2.COLOR_BGR2GRAY)
    # Keep the original color image for review; OCR uses a sharpened grayscale copy.
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    ocr_input = image_path.with_name(image_path.stem + "_ocr_input.png")
    if not cv2.imwrite(str(ocr_input), gray):
        raise RuntimeError("Could not write temporary OCR image")
    try:
        result = subprocess.run(
            ["tesseract", str(ocr_input), "stdout", "-l", "jpn", "--psm", "11", "tsv"],
            check=True, capture_output=True, text=True, encoding="utf-8"
        )
    finally:
        ocr_input.unlink(missing_ok=True)

    groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    reader = csv.DictReader(result.stdout.splitlines(), delimiter="\t")
    for row in reader:
        text = (row.get("text") or "").strip()
        try:
            confidence = float(row.get("conf", "-1"))
            left, top = int(row["left"]), int(row["top"])
            w, h = int(row["width"]), int(row["height"])
        except (ValueError, KeyError):
            continue
        if not text or confidence < 0 or w <= 0 or h <= 0:
            continue
        key = (row.get("block_num", ""), row.get("par_num", ""),
               row.get("line_num", ""), row.get("page_num", ""))
        groups[key].append({
            "text": text, "confidence": confidence,
            "left": left // scale, "top": top // scale,
            "right": (left + w + scale - 1) // scale,
            "bottom": (top + h + scale - 1) // scale,
        })

    lines = []
    for words in groups.values():
        text = "".join(word["text"] for word in words)
        if not normalize(text):
            continue
        lines.append({
            "text": text,
            "confidence": round(sum(w["confidence"] for w in words) / len(words), 1),
            "bounds": {
                "left": min(w["left"] for w in words),
                "top": min(w["top"] for w in words),
                "right": max(w["right"] for w in words),
                "bottom": max(w["bottom"] for w in words),
            },
        })
    lines.sort(key=lambda line: (line["bounds"]["top"], line["bounds"]["left"]))
    return lines


def match_catalog(lines: list[dict], items: list[dict]) -> list[dict]:
    names = [(item["itemId"], item["itemName"], normalize(item["itemName"])) for item in items]
    for line in lines:
        candidate = normalize(line["text"])
        ranked = sorted(
            ((difflib.SequenceMatcher(None, candidate, name).ratio(), item_id, name_jp)
             for item_id, name_jp, name in names),
            reverse=True
        )
        if ranked and ranked[0][0] >= 0.38:
            score, item_id, item_name = ranked[0]
            line["bestCatalogMatch"] = {
                "itemId": item_id, "itemName": item_name, "similarity": round(score, 3)
            }
        else:
            line["bestCatalogMatch"] = None
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    args = parser.parse_args()

    seeds = json.loads(args.seeds.read_text(encoding="utf-8"))
    lines = match_catalog(run_tesseract(args.image), seeds["items"])
    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    for index, line in enumerate(lines, 1):
        b = line["bounds"]
        cv2.rectangle(image, (b["left"], b["top"]), (b["right"], b["bottom"]), (255, 220, 0), 1)
        label = str(index)
        match = line.get("bestCatalogMatch")
        if match:
            label += ":" + match["itemName"]
        cv2.putText(image, label, (b["left"], max(12, b["top"] - 3)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.32, (255, 220, 0), 1, cv2.LINE_AA)

    result = {
        "stageId": seeds["stageId"],
        "sourceImage": str(args.image),
        "purpose": "diagnostic_text_position_anchors_only",
        "runtimeEnabled": False,
        "lineCount": len(lines),
        "matchedCatalogCount": sum(1 for line in lines if line.get("bestCatalogMatch")),
        "lines": lines,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.preview), image, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit(f"Could not write preview: {args.preview}")
    print(f"OCR extracted {len(lines)} text lines; {result['matchedCatalogCount']} have a tentative catalog match.")


if __name__ == "__main__":
    main()
