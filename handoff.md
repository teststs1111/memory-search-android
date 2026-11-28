# Coordinate registration handoff

Last reviewed: 2026-11-28

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

## Chapter 8 review

- Chapter: 第8章「ゲームセンター(閉店)」.
- The original annotated and clean JPEG pair was fetched unchanged from the atwiki attachment URLs recorded in `app/src/main/assets/stages/chapter_8_label_boxes.candidates.json`. Both files are 1206×2144; their SHA-256 hashes are stored with the candidate data and checked by the review workflow.
- Added 33 catalog-ordered entries to `chapter_8_label_boxes.candidates.json`. 32 have manually traced candidate rectangles in the established 563×1000 coordinate basis; 26 have complete visible boundaries and six remain pending because their label backings touch an image edge: 星型クッション, ゲーム機張り紙, 作業用手袋, ドライバー, レンチ, ハンマー.
- The reference image contains a visible ポップコーン annotation label that is not in the Chapter 8 catalog, while the catalog item ネジ has no matching annotation label. Both discrepancies are recorded explicitly. No coordinate was invented for ネジ and the catalog was not silently changed.
- Twenty-one intersections between axis-aligned candidate bounds are recorded. Some are expected from rotated/adjacent label backings; none were auto-corrected.
- Candidate boxes were rendered against both the annotated and clean images at the same source dimensions. The preview confirms the 32 traced boxes map to the corresponding visible scene regions; this is an offline visual review, not a device alignment test.
- `app/src/main/assets/stages/chapter_8.json` remains `awaiting_coordinate_verification` with an empty `items` array. No Chapter 8 coordinates are enabled at runtime.
- Added seven focused Chapter 8 review tests; all seven passed locally. Added a branch-only, read-only review workflow that downloads and hash-checks the original pair, runs all Python tests plus catalog/dataset validators, renders the comparison, and uploads the sources/previews as an artifact.
- No real-device test has been performed.

## Chapter 9 review confirmation

- The existing Chapter 9 candidate dataset and aligned annotated/base comparison were rechecked from the exact source pair. The latest review workflow run 45963659191 completed successfully; artifact 15181338666 contains the source pair and comparison.
- Chapter 9 remains candidate-only: 28 complete boxes, three edge-clipped boxes (クッション, プリン, 作業用手袋), two near-edge mappings (ヘッドホン, タブレット), and missing catalog item ランチ. The two extra annotated labels 救急箱 and ハサミ remain recorded separately. Eleven axis-aligned overlap pairs remain unadjusted.
- `app/src/main/assets/stages/chapter_9.json` remains empty and awaiting verification. No Chapter 9 coordinates are enabled at runtime.

## Chapter 10 review

- Chapter: 第10章「第２沿岸区域」.
- Exact atwiki source pair: annotated `reference/chapter_10/annotated.jpg` (2016×2520; SHA-256 `c10ffa2a046edbe6bb0b948d3a4ad27fbb3ca48fbc0898dba8709971fcc199ac`) and clean base `reference/chapter_10/base.jpg` (1404×2496; SHA-256 `a7596c060e330d5f69b3e079a5218a00487b6b83747bfdef94d634b4a453cc55`).
- The annotated image was aligned to the clean base with SIFT/RANSAC: 3302 good matches, 3244 inliers, 0.982435 inlier ratio. Candidate rectangles were traced from the visible annotation backings, mapped through the homography, and normalized to the 563×1000 coordinate basis.
- Added 35 catalog-ordered candidate records. 30 boxes have complete visible boundaries; three are edge-clipped (トランシーバー and ロープ at the left edge, レンチ at the bottom edge); 木片 maps within six basis pixels of the clean base's right edge and remains near-edge pending; the catalog item バケツ has no distinct visible annotation backing. 青いバケツ is recorded with reference-only lines `バケツ` / `青`.
- Nineteen axis-aligned candidate overlaps are recorded without automatic correction. The detector was not used as a coordinate source.
- `app/src/main/assets/stages/chapter_10.json` remains `awaiting_coordinate_verification` with an empty `items` array. The Chapter 10 candidate file is explicitly runtime-disabled. No Chapter 10 coordinates are enabled for gameplay.

## Next work

1. Search for fuller or alternate Chapter 10 annotation material to resolve トランシーバー, ロープ, レンチ, 木片, and the separate catalog item バケツ. If no better source exists, leave them pending.
2. Search for uncropped references that could resolve the existing Chapter 6–9 edge-clipped and missing-label cases, in chapter order. Do not infer missing boundaries.
3. Keep Chapters 6–10 runtime datasets empty until every label box in a chapter is fully grounded. Preserve the Chapter 5 baseline and all runtime matching/highlight behavior.
