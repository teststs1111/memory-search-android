#!/usr/bin/env python3
"""Extract Japanese text line positions from annotated reference images.

This is a diagnostic stage only: OCR boxes are anchors for locating labels,
not substitutes for the translucent label-frame boundaries.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import io
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import cv2
from detect_label_frames import align_annotated_to_base


def normalize(text: str) -> str:
    return re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠ー]", "", text).lower()


def run_tesseract(image_path: Path, base_path: Path, scale: int = 4) -> list[dict]:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    base = cv2.imread(str(base_path), cv2.IMREAD_COLOR)
    if image is None or base is None:
        raise ValueError(f"Could not read annotated/base image: {image_path}, {base_path}")
    image = align_annotated_to_base(image, base)
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
    reader = csv.DictReader(io.StringIO(result.stdout), delimiter="\t")
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


def run_seeded_tesseract(image: "cv2.Mat", item: dict, image_size: dict, scale: int = 5) -> dict:
    height, width = image.shape[:2]
    if "sourceRect" in item:
        x1, y1, x2, y2 = item["sourceRect"]
        sx, sy = width / image_size["width"], height / image_size["height"]
        x1, y1, x2, y2 = int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)
    else:
        b = item["bounds"]
        x1, y1 = int(b["left"] * width), int(b["top"] * height)
        x2, y2 = int(b["right"] * width), int(b["bottom"] * height)
    pad_x, pad_y = max(8, (x2 - x1) // 4), max(8, (y2 - y1) // 3)
    left, top = max(0, x1 - pad_x), max(0, y1 - pad_y)
    right, bottom = min(width, x2 + pad_x), min(height, y2 + pad_y)
    crop = image[top:bottom, left:right]
    enlarged = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(enlarged, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    temp = Path("/tmp") / f"memory-search-ocr-{item['itemId']}.png"
    if not cv2.imwrite(str(temp), gray):
        return {"itemId": item["itemId"], "text": "", "confidence": 0, "bounds": None}
    try:
        result = subprocess.run(
            ["tesseract", str(temp), "stdout", "-l", "jpn", "--psm", "11", "tsv"],
            check=True, capture_output=True, text=True, encoding="utf-8"
        )
    finally:
        temp.unlink(missing_ok=True)
    words = []
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        text = (row.get("text") or "").strip()
        try:
            conf = float(row.get("conf", "-1"))
            l, t, w, h = int(row["left"]), int(row["top"]), int(row["width"]), int(row["height"])
        except (ValueError, KeyError):
            continue
        if text and conf >= 0 and w > 0 and h > 0:
            words.append((text, conf, l, t, w, h))
    if not words:
        return {"itemId": item["itemId"], "text": "", "confidence": 0, "bounds": None}
    recognized = "".join(word[0] for word in words)
    bounds = {
        "left": left + min(w[2] for w in words) // scale,
        "top": top + min(w[3] for w in words) // scale,
        "right": left + (max(w[2] + w[4] for w in words) + scale - 1) // scale,
        "bottom": top + (max(w[3] + w[5] for w in words) + scale - 1) // scale,
    }
    score = difflib.SequenceMatcher(None, normalize(recognized), normalize(item["itemName"])).ratio()
    return {
        "itemId": item["itemId"], "itemName": item["itemName"],
        "text": recognized, "confidence": round(sum(w[1] for w in words) / len(words), 1),
        "similarity": round(score, 3), "bounds": bounds,
    }


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
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--seeds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    args = parser.parse_args()

    seeds = json.loads(args.seeds.read_text(encoding="utf-8"))
    base_image = cv2.imread(str(args.base), cv2.IMREAD_COLOR)
    annotated_image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if base_image is None or annotated_image is None:
        raise ValueError("Could not load aligned preview images")
    aligned_annotated = align_annotated_to_base(annotated_image, base_image)
    lines = match_catalog(run_tesseract(args.image, args.base), seeds["items"])
    item_anchors = [
        run_seeded_tesseract(aligned_annotated, item, seeds["imageSize"])
        for item in seeds["items"]
    ]
    image = base_image.copy()
    for anchor in item_anchors:
        if anchor.get("bounds"):
            b = anchor["bounds"]
            cv2.rectangle(image, (b["left"], b["top"]), (b["right"], b["bottom"]), (255, 220, 0), 1)
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
        "seededItemAnchorCount": sum(1 for anchor in item_anchors if anchor.get("bounds")),
        "itemAnchors": item_anchors,
        "lines": lines,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.preview.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.preview), image, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise SystemExit(f"Could not write preview: {args.preview}")
    print(f"OCR extracted {len(lines)} text lines; {result['matchedCatalogCount']} tentative matches; {result['seededItemAnchorCount']}/{len(item_anchors)} seeded item crops returned text.")


if __name__ == "__main__":
    main()
