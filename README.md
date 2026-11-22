# Memory Search Android

Android companion app for the E.D.E.N. Memory Search minigame.

## Milestone 1

Create a phone-managed Android project that builds in GitHub Actions. The first functional target is Chapter 1 only.

## Planned features

- Explicit stage selection; each stage has its own coordinate dataset.
- OCR of the requested item name.
- Stage-scoped item lookup.
- Transparent marker overlay that does not intercept game touch input.
- Normalized coordinates mapped to the detected game content area.

## Data integrity

Chapter 1 source images were shared in the project discussion. Item names and coordinates still require direct verification before they are treated as production data. Unverified items must never trigger a marker. Example coordinates must be clearly marked as examples.

## Android permissions

Screen capture uses the MediaProjection consent flow. Overlay display requires the user's explicit Android special-access grant. Capture must stop when the user ends the session or Android revokes projection.

## Build

Pushes to `main` and manual workflow runs build a debug APK with GitHub Actions. Download it from the workflow run's Artifacts section.
