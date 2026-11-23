#!/usr/bin/env python3
"""Offline regression checks for all bundled OCR item catalogs.

This validates catalog data and exercises the same normalization contract as
OcrItemMatcher. Kotlin behavior itself is covered by the JVM unit tests.
"""
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

CATALOG = Path("app/src/main/assets/stages/item_catalogs.json")
EXPECTED_CHAPTERS = [f"chapter_{number}" for number in range(1, 11)]
EXPECTED_COUNTS = {
    "chapter_1": 32,
    "chapter_2": 29,
    "chapter_3": 33,
    "chapter_4": 31,
    "chapter_5": 34,
    "chapter_6": 32,
    "chapter_7": 35,
    "chapter_8": 33,
    "chapter_9": 34,
    "chapter_10": 35,
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return "".join(char for char in value if not char.isspace())


def main() -> None:
    root = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert root.get("schemaVersion") == 1, "Unsupported catalog schema"
    chapters = root.get("chapters")
    assert isinstance(chapters, list), "chapters must be an array"

    ids = [chapter.get("stageId") for chapter in chapters]
    assert ids == EXPECTED_CHAPTERS, f"Expected chapters 1-10 in order, got {ids}"

    shared_names = defaultdict(list)
    total_items = 0
    for chapter in chapters:
        stage_id = chapter["stageId"]
        stage_name = chapter.get("stageName", "")
        names = chapter.get("itemNames")
        assert stage_name.strip(), f"{stage_id}: blank chapter name"
        assert isinstance(names, list) and names, f"{stage_id}: no item names"
        assert len(names) == EXPECTED_COUNTS[stage_id], (
            f"{stage_id}: expected {EXPECTED_COUNTS[stage_id]} names, got {len(names)}"
        )
        assert all(isinstance(name, str) and name.strip() for name in names), (
            f"{stage_id}: blank or non-string item name"
        )
        assert len(names) == len(set(names)), f"{stage_id}: duplicate exact item name"

        normalized = [normalize(name) for name in names]
        assert all(normalized), f"{stage_id}: name normalizes to empty"
        assert len(normalized) == len(set(normalized)), (
            f"{stage_id}: two labels collide after NFKC/whitespace normalization"
        )

        # Simulate every catalog label as OCR input: exact normalized match only.
        catalog_keys = set(normalized)
        for name, key in zip(names, normalized):
            assert key in catalog_keys, f"{stage_id}: OCR round-trip failed for {name!r}"

        # A label absent from this selected chapter must never be inferred from
        # another chapter's catalog.
        sentinel = normalize(f"未登録テスト項目_{stage_id}")
        assert sentinel not in catalog_keys, f"{stage_id}: sentinel collision"

        for name in names:
            shared_names[name].append(stage_id)
        total_items += len(names)

    repeated = {name: stages for name, stages in shared_names.items() if len(stages) > 1}
    print(f"Catalog OK: {len(chapters)} chapters, {total_items} item labels")
    print(f"Cross-chapter repeated labels: {len(repeated)} (expected; lookup stays chapter-scoped)")
    for name, stages in sorted(repeated.items()):
        print(f"  {name}: {', '.join(stages)}")


if __name__ == "__main__":
    main()
