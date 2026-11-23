#!/usr/bin/env python3
"""Validate runtime stage datasets and inactive label-box candidates."""
import json
import math
import re
from pathlib import Path

STAGES_DIR = Path("app/src/main/assets/stages")
EXPECTED_STAGE_IDS = [f"chapter_{number}" for number in range(1, 11)]
STAGE_FILE = re.compile(r"^chapter_(\d+)\.json$")
CANDIDATE_FILE = re.compile(r"^chapter_(\d+)_label_boxes\.candidates\.json$")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_runtime_datasets() -> None:
    files = sorted(
        (path for path in STAGES_DIR.iterdir() if STAGE_FILE.fullmatch(path.name)),
        key=lambda path: int(STAGE_FILE.fullmatch(path.name).group(1)),
    )
    expected_files = [f"chapter_{number}.json" for number in range(1, 11)]
    actual_files = [path.name for path in files]
    assert actual_files == expected_files, (
        f"Expected exactly runtime datasets {expected_files}, got {actual_files}"
    )

    for expected_id, path in zip(EXPECTED_STAGE_IDS, files):
        data = read_json(path)
        assert data.get("stageId") == expected_id, f"{path}: wrong stageId"
        assert isinstance(data.get("stageName"), str) and data["stageName"].strip(), (
            f"{path}: blank stageName"
        )
        assert data.get("coordinateSystem") == "normalized_0_to_1", (
            f"{path}: unsupported coordinateSystem"
        )
        assert isinstance(data.get("referenceImage"), str) and data["referenceImage"].strip(), (
            f"{path}: blank referenceImage"
        )
        status = data.get("dataStatus")
        assert status in {"awaiting_coordinate_verification", "verified"}, (
            f"{path}: unsupported dataStatus {status!r}"
        )
        items = data.get("items")
        assert isinstance(items, list), f"{path}: items must be an array"
        if status == "awaiting_coordinate_verification":
            assert not items, f"{path}: unverified coordinates must remain empty"
            continue

        ids = set()
        for item in items:
            assert isinstance(item, dict), f"{path}: item must be an object"
            item_id = item.get("itemId")
            item_name = item.get("itemName")
            assert isinstance(item_id, str) and item_id.strip(), f"{path}: blank itemId"
            assert item_id not in ids, f"{path}: duplicate itemId {item_id}"
            ids.add(item_id)
            assert isinstance(item_name, str) and item_name.strip(), (
                f"{path}: blank itemName for {item_id}"
            )
            for axis in ("x", "y"):
                value = item.get(axis)
                assert isinstance(value, (int, float)) and math.isfinite(value), (
                    f"{path}: {item_id} has invalid {axis}"
                )
                assert 0.0 <= value <= 1.0, f"{path}: {item_id} {axis} outside 0..1"


def validate_inactive_candidates() -> None:
    files = sorted(
        (path for path in STAGES_DIR.iterdir() if CANDIDATE_FILE.fullmatch(path.name)),
        key=lambda path: int(CANDIDATE_FILE.fullmatch(path.name).group(1)),
    )
    for path in files:
        data = read_json(path)
        chapter_number = int(CANDIDATE_FILE.fullmatch(path.name).group(1))
        assert data.get("stageId") == f"chapter_{chapter_number}", (
            f"{path}: stageId does not match filename"
        )
        assert data.get("coordinateSystem") == "normalized_0_to_1", (
            f"{path}: unsupported coordinateSystem"
        )
        assert data.get("purpose") == "highlight_item_name_label_box", (
            f"{path}: candidate purpose must be label-frame highlighting"
        )
        assert data.get("runtimeEnabled") is False, (
            f"{path}: candidate boxes must not be enabled at runtime"
        )
        assert data.get("dataStatus") != "verified", (
            f"{path}: candidate boxes are not runtime-verified coordinates"
        )
        image_size = data.get("imageSize")
        assert isinstance(image_size, dict), f"{path}: missing imageSize"
        width, height = image_size.get("width"), image_size.get("height")
        assert isinstance(width, int) and width > 0, f"{path}: invalid image width"
        assert isinstance(height, int) and height > 0, f"{path}: invalid image height"

        items = data.get("items")
        assert isinstance(items, list) and items, f"{path}: no candidate boxes"
        ids = set()
        for item in items:
            item_id = item.get("itemId")
            assert isinstance(item_id, str) and item_id.strip(), f"{path}: blank itemId"
            assert item_id not in ids, f"{path}: duplicate itemId {item_id}"
            ids.add(item_id)
            assert isinstance(item.get("itemName"), str) and item["itemName"].strip(), (
                f"{path}: blank itemName for {item_id}"
            )
            bounds = item.get("bounds")
            assert isinstance(bounds, dict), f"{path}: missing bounds for {item_id}"
            coords = [bounds.get(key) for key in ("left", "top", "right", "bottom")]
            assert all(
                isinstance(value, (int, float)) and math.isfinite(value)
                for value in coords
            ), f"{path}: invalid bounds for {item_id}"
            left, top, right, bottom = coords
            assert 0.0 <= left < right <= 1.0, f"{path}: invalid horizontal bounds for {item_id}"
            assert 0.0 <= top < bottom <= 1.0, f"{path}: invalid vertical bounds for {item_id}"

    print(f"Inactive candidate datasets OK: {len(files)} file(s); runtimeEnabled remains false")


def main() -> None:
    validate_runtime_datasets()
    validate_inactive_candidates()
    print("Runtime stage datasets OK: 10 chapters; unverified coordinate sets remain empty")


if __name__ == "__main__":
    main()
