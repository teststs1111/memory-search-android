# Coordinate registration handoff

Last reviewed: 2026-11-26

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
- The difference-mask detector returned 31/32 items and missed 水筒. 水筒 is a red annotated label; its candidate was visually matched manually. Detector output is diagnostic only and is not used as the coordinate source.
- Every candidate's normalized bounds exactly match its integer `sourceRect` against the 563×1000 reference.
- `app/src/main/assets/stages/chapter_6.json` remains `awaiting_coordinate_verification` with an empty `items` array. No Chapter 6 coordinates are enabled at runtime.
- The source image itself is edge-cropped for the five pending labels. Search for an uncropped/alternate reference before promoting those five; do not infer missing frame edges.

## Workflow safety and validation

- Chapter 6 render and detector workflows previously checked out/pushed `main` with `contents: write`. They must remain branch-only, read-only, and artifact-upload-only on this working branch.
- Added a same-scale annotated/base comparison preview and focused Chapter 6 candidate-review tests.
- Latest known branch validation before this handoff: run 45724732757 at commit `2735e04aee836266da423592ff26aef1b63259ed`. Catalog validation, stage validation, Kotlin unit tests, and debug APK build succeeded. The Chapter 5 ML Kit instrumented job failed after the test started with an instrumentation process crash; it is not a successful OCR verification.
- No real-device test has been performed.

## Next work

1. Look for an alternate or uncropped Chapter 6 reference that fully shows the five edge-touching label frames. If none exists, keep those five pending.
2. Do not populate the Chapter 6 runtime dataset until every promoted box is grounded in a complete visible frame.
3. Continue with Chapter 7 only after Chapter 6's remaining source ambiguity is resolved; then proceed through Chapters 8–10 in order.
4. Keep Chapter 5's user-approved boxes unchanged unless a clear source-image defect is found.
