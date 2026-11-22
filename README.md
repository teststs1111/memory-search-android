# Memory Search Android

Android companion app for the E.D.E.N. Memory Search minigame.

## Current milestone

- The app loads stage JSON files from `app/src/main/assets/stages/`.
- The stage selector is populated from the available JSON datasets.
- Item lookup is scoped to the selected stage; identical item names in different stages remain independent.
- Only datasets marked `verified` can return marker candidates.
- Coordinates use `normalized_0_to_1`, relative to the game-content area.
- Unit tests cover coordinate validation, duplicate IDs, stage isolation, and unverified-data safety.

## Reference images — upload instructions

There are currently 10 chapters prepared. Upload the original images into the matching folders under **`reference/`**. These folders are separate from the app assets, so reference images will not be bundled into the APK.

For each chapter, upload these three files:

| Filename | What to upload |
|---|---|
| `base.jpg` | The unannotated/full stage image |
| `left.jpg` | The left annotated reference image |
| `right.jpg` | The right annotated reference image |

Folder examples:

- `reference/chapter_01/`
- `reference/chapter_02/`
- …
- `reference/chapter_10/`

**You do not need to combine left and right.** Upload them separately as-is; I will align and combine them into one annotated reference image during data preparation. Please keep the original resolution and do not crop, resize, or recompress them. PNG is also fine; if you use PNG, keep the same base names (for example, `left.png`) and tell me.

On GitHub Mobile, open the relevant chapter folder, choose **Add file → Upload files**, select the three images, and commit. Repeat only for chapters whose images you have ready; you do not need to upload all ten at once.

## Stage data status

All ten chapter JSON files are prepared as `awaiting_coordinate_verification` with empty item lists. This is intentional. No item names or coordinates are guessed. After the reference images are checked, verified item coordinates will be added to the corresponding chapter dataset.

Each JSON file in `app/src/main/assets/stages/` represents one selectable chapter:

- `stageId`: stable unique chapter identifier.
- `stageName`: label shown in the app.
- `coordinateSystem`: currently `normalized_0_to_1`.
- `referenceImage`: path to the unannotated reference image under `reference/`.
- `dataStatus`: `awaiting_coordinate_verification` or `verified`.
- `items`: list of `itemId`, `itemName`, `x`, and `y` for verified target-object marker coordinates.

Chapter 1 also has a separate `chapter_1_label_boxes.candidates.json` asset containing 32 normalized rectangles for the **item-name label frames**. These are intended to be highlighted as a whole when OCR recognizes the matching name. This candidate file is deliberately marked `runtimeEnabled: false` and is not read by the current app yet; it must not be treated as verified runtime data.

An unverified dataset must have an empty `items` array. The validator enforces this, and unverified data cannot produce lookup results or markers.

## Not implemented yet

- MediaProjection screen capture.
- Japanese OCR and OCR confidence/retry handling.
- Transparent overlay marker.
- Mapping between the captured game-content rectangle and normalized coordinates.

These features will be added after the chapter reference data is verified.

## Build and install

GitHub Actions runs unit tests and builds a debug APK on pushes to `main`. Open the latest successful workflow run, then download the `memory-search-android-debug` artifact from its Artifacts section. The APK is currently a debug build, not a Play Store release.

## Network and game isolation

The companion app does not request Android's `INTERNET` permission and does not communicate with the game. Stage datasets are bundled locally. CI checks the app manifest so an accidental addition of the internet permission fails the build.

## Chapter 1 label-box candidates

- The 32 item-name label frames have been mapped from the original `left.jpg` / `right.jpg` annotations onto `base.jpg`.
- Candidate rectangles are stored separately in `app/src/main/assets/stages/chapter_1_label_boxes.candidates.json` using normalized `left`, `top`, `right`, and `bottom` bounds.
- These rectangles identify the name plates, not the physical target objects.
- They remain review-only (`runtimeEnabled: false`) until the rectangle overlay is implemented and the remaining small alignment differences are checked.
