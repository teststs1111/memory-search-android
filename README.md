# Memory Search Android

Android companion app for the E.D.E.N. Memory Search minigame.

## Current milestone

- Android app can load stage JSON files from `app/src/main/assets/stages/`.
- The stage selector is populated from the available JSON datasets.
- Item lookup is scoped to the selected stage; identical item names in different stages remain independent.
- Only datasets marked `verified` can return marker candidates.
- Coordinates are normalized to the game-content rectangle, from 0.0 to 1.0.
- Unit tests cover coordinate validation, duplicate IDs, stage isolation, and unverified-data safety.

## Chapter 1 data status

Chapter 1 is currently `awaiting_coordinate_verification` with an empty item list. This is intentional: the source images need direct visual verification before item names and coordinates are added. No guessed coordinates or unverified items are used.

## Data format

Each JSON file in `app/src/main/assets/stages/` represents one selectable stage:

- `stageId`: stable unique stage identifier.
- `stageName`: label shown in the app.
- `coordinateSystem`: currently `normalized_0_to_1`.
- `referenceImage`: source image used to establish coordinates.
- `dataStatus`: `awaiting_coordinate_verification` or `verified`.
- `items`: list of `itemId`, `itemName`, `x`, and `y`.

An unverified dataset must have an empty `items` array. This is checked by the validator.

## Not implemented yet

- MediaProjection screen capture.
- Japanese OCR and OCR confidence/retry handling.
- Transparent overlay marker.
- Mapping between the captured game-content rectangle and normalized coordinates.

These features are intentionally kept separate from the current data-loading milestone.

## Build and install

GitHub Actions runs unit tests and builds a debug APK on pushes to `main`. Open the latest successful workflow run, then download the `memory-search-android-debug` artifact from its Artifacts section. The APK is currently a debug build, not a Play Store release.

## Network and game isolation

The companion app does not request Android's `INTERNET` permission and does not communicate with the game. Stage datasets are bundled locally. CI checks the app manifest so an accidental addition of the internet permission fails the build.
