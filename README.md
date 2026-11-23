# Memory Search Android

Android companion app for the E.D.E.N. Memory Search minigame.

## Current implementation

- The app loads and displays all 10 chapter datasets from `app/src/main/assets/stages/chapter_N.json`.
- The item-name catalog is stored separately in `item_catalogs.json` and lookup is strictly scoped to the chapter selected when capture is started.
- The chapter ID is carried through the screen-capture service and returned with the OCR result, so changing the selector while capture is running cannot silently change the lookup chapter.
- A user-approved, one-shot Android MediaProjection capture is processed in memory by Japanese ML Kit OCR.
- OCR matching is exact after Unicode NFKC normalization and whitespace removal. Two adjacent OCR lines may be joined only within the same OCR text block; lines from separate blocks are never joined.
- Captured images are not saved or transmitted. The bitmap, ImageReader, VirtualDisplay, MediaProjection, worker thread, and OCR recognizer are released after the one-shot operation.
- The app does not request Android's `INTERNET` permission. Stage data and OCR processing are local.
- GitHub Actions validates all 10 OCR catalogs (chapter order, expected item counts, blank/duplicate labels, normalization collisions, and per-label exact-match round trips), runs Kotlin unit tests, and builds a debug APK on pushes to `main`.

## Chapter data

There are 10 prepared chapter slots. Each chapter JSON currently remains `awaiting_coordinate_verification` with an empty `items` array. This is intentional: unverified object coordinates are never used at runtime.

The item-name catalog is independent of coordinate data. It contains the OCR lookup names for each chapter, allowing the OCR test to work without activating unverified coordinates.

Chapter 1 also has a separate `chapter_1_label_boxes.candidates.json` file containing 32 candidate rectangles for the **item-name label frames** (not the hidden physical objects). The candidate data is marked `runtimeEnabled: false` and is used only by the developer preview. Numbered circles are preview-only and are never drawn over the game.

## Reference images — upload instructions

There are 10 chapter folders prepared under `reference/`. Upload the original images into the matching folder. These reference folders are separate from the app assets, so the images are not bundled into the APK.

For each chapter, upload these three files:

| Filename | What to upload |
|---|---|
| `base.jpg` | The unannotated/full stage image |
| `left.jpg` | The left annotated reference image |
| `right.jpg` | The right annotated reference image |

Examples: `reference/chapter_01/` through `reference/chapter_10/`.

You do not need to combine the left and right images. Upload them separately as-is; preserve the original resolution and do not crop, resize, or recompress them. PNG is also fine if the same base names are used and the format is communicated.

## Remaining work

- Review and finalize candidate label-frame rectangles against the paired reference images, chapter by chapter.
- Implement a safe mapping from the captured game-content rectangle to normalized label-frame coordinates.
- Implement a transparent, non-touchable label-frame highlight overlay only after the corresponding chapter coordinates are verified.
- Add OCR confidence/retry handling only if real event captures show that the current exact matcher needs it.
- Perform the first full in-game validation at the next event. Until then, keep all unverified label-frame coordinates disabled.

No hidden-object target coordinates are used for label highlighting. The intended runtime behavior is to highlight the complete item-name label frame only; it must not draw numbered circles or highlight the physical hidden object.

## Build and install

GitHub Actions builds a debug APK. Open the latest successful workflow run and download the `memory-search-android-debug` artifact from its Artifacts section. This is a debug build, not a Play Store release. Artifact retention is limited by GitHub Actions.

## Network and game isolation

The companion app does not request Android's `INTERNET` permission and does not communicate with the game. Stage datasets are bundled locally. CI checks the app manifest so an accidental addition of the internet permission fails the build.
