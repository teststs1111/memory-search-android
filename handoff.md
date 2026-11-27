# Coordinate registration handoff

Last reviewed: 2026-11-27

## Repository guardrails

- Repository: `teststs1111/memory-search-android`
- Working branch: `fix/geometry-aware-two-line-ocr`
- Keep `main` unchanged. Do not merge, close, or open another PR.
- Existing draft PR: [#1 — explicit per-item rules for two-line reference OCR](https://github.com/teststs1111/memory-search-android/pull/1)
- Runtime OCR reads the three single-line labels in the bottom target strip only. Reference-image two-line parsing is separate.
- Gameplay must map recognized names to pre-registered coordinates. Do not add per-play board/frame/label coordinate detection.
- Chapters 1–4 remain deferred.

## Chapter 5 baseline

- Runtime dataset: `app/src/main/assets/stages/chapter_5.json`, 34 items, `dataStatus: verified`.
- Reference pair: `reference/chapter_05/annotated.jpg` and `reference/chapter_05/base.jpg`, 563×1000 coordinate basis.
- The user's requested 双眼鏡 correction is currently `sourceRect: [446, 568, 542, 608]`, normalized bounds `left=0.7922, top=0.568, right=0.9627, bottom=0.608`. This aligns with the visible purple label rectangle in the committed annotated reference; the other 33 candidate boxes were preserved.
- The Chapter 5 source-image alignment is reviewed offline only. Actual phone overlay alignment and live OCR behavior have not been device-verified.

## Chapter 6 review

- Chapter: 第6章「学園の中庭」.
- Reference pair: `reference/chapter_06/annotated.jpg` and `reference/chapter_06/base.jpg`, both 1404×2496. Candidate `imageSize`/`sourceRect` use the original 563×1000 coordinate basis; the render tool maps the normalized bounds onto the larger source pair after checking the matching aspect ratio.
- Catalog and candidate list contain 32 items in the same order.
- The 32 label identities/placements were reviewed against the annotated image and clean base at the same scale. 27 candidate boxes have complete visible boundaries.
- Five boxes touch the image boundary and remain pending because the full label-frame extent cannot be established from this image:
  - バードフィーダー (right edge)
  - ハンカチ (right edge)
  - スクールバッグ (right edge)
  - 鉢植え (left edge)
  - ラケット (right edge)
- Fourteen overlapping candidate pairs are recorded in `chapter_6_label_boxes.candidates.json`; these are retained for review and were not automatically adjusted.
- The latest branch detector run (45767830077) associated 32/32 seeds, but its preview rectangles are oversized/contaminated by nearby scene objects. No detector bounds were copied into the coordinate candidates. 水筒 is a red annotated label and its candidate remains visually grounded from the annotated image.
- Every candidate's normalized bounds exactly match its integer `sourceRect` against the 563×1000 reference.
- `app/src/main/assets/stages/chapter_6.json` remains `awaiting_coordinate_verification` with an empty `items` array. No Chapter 6 coordinates are enabled at runtime.
- The source image itself is edge-cropped for the five pending labels. Search for an uncropped/alternate reference before promoting those five; do not infer missing frame edges.


## Chapter 7 review

- Chapter: 第7章「心理評価センター」.
- Reference pair: `reference/chapter_07/annotated.jpg` and `reference/chapter_07/base.jpg`, both 1206×2144. Candidate coordinates use the established 563×1000 normalized basis and retain the actual source dimensions in metadata.
- Added `app/src/main/assets/stages/chapter_7_label_boxes.candidates.json` with all 35 catalog items in catalog order. Coordinates were manually traced from the annotated label backings and compared with the clean base; the OCR text-region diagnostic and connected-component detector were not used as coordinate sources.
- 25 candidate boxes have complete visible boundaries. Ten remain explicitly pending because the backing rectangle touches an image edge: ビーチボール, 壊れたロボット, 卓上カレンダー, ハサミ, ストップウォッチ, メガネ, ゴーグル, ルービックキューブ, 救急箱, ボールペン.
- 26 intersections are recorded between axis-aligned candidate bounds. Several source labels are rotated or adjacent; no overlap was auto-corrected. These overlaps are review metadata, not evidence that the original label backings physically overlap.
- The earlier OCR diagnostic found only 14 merged regions and four catalog matches; it remains diagnostic-only. A separate annotation-fill detector was added for visual diagnostics, but its components were not copied into candidate coordinates.
- `app/src/main/assets/stages/chapter_7.json` remains `awaiting_coordinate_verification` with an empty `items` array. No Chapter 7 coordinates are enabled at runtime.
- Added candidate-review tests and a clean-base/annotated comparison renderer. The Chapter 7 review workflow is branch-only, read-only, and uploads previews as an artifact.

## Workflow safety and validation

- Chapter 6 render and detector workflows previously checked out/pushed `main` with `contents: write`. They must remain branch-only, read-only, and artifact-upload-only on this working branch.
- Added a same-scale annotated/base comparison preview and focused Chapter 6 candidate-review tests.
- At commit `cc598825ffa0481324053294687b61793841ef8a`, the catalog validator, stage validator, Kotlin unit tests, debug APK build, 17 Python detector/review tests, Chapter 6 detection job, and Chapter 6 render/comparison job succeeded. The Chapter 5 ML Kit instrumented job was still running at last check; earlier run 45724732757 failed after the test started with an instrumentation process crash, so no emulator OCR pass is claimed.
- No real-device test has been performed.

## Next work

1. Continue Chapter 8 candidate generation and visual review using its annotated/clean source pair; Chapters 6 and 7 may remain partially pending while later chapters progress.
2. Keep the five clipped Chapter 6 boxes and ten clipped Chapter 7 boxes pending until an uncropped reference is found; do not infer missing edges or enable incomplete runtime datasets.
3. Proceed through Chapters 9–10 in order after Chapter 8.
4. Keep Chapter 5's user-approved boxes unchanged unless a clear source-image defect is found.
