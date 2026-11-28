# Chapter 8 reference source

The current full reference pair is fetched unchanged by the Chapter 8 review workflow:

- Annotated: https://img.atwiki.jp/eden_jp/attach/46/155/%E7%AC%AC8%E7%AB%A0.jpeg
- Clean base: https://img.atwiki.jp/eden_jp/attach/46/152/%E7%AC%AC8%E7%AB%A0%E7%84%A1%E5%8A%A0%E5%B7%A5.jpeg

Both originals are JPEG, 1206×2144. Their SHA-256 values are recorded in
`chapter_8_label_boxes.candidates.json` and checked before preview generation.
The workflow downloads them into this folder as `annotated.jpg` and `base.jpg`;
the downloaded binaries are retained in the workflow artifact rather than committed
to the source branch.

The older `left.jpg` / `right.jpg` upload plan is not used for this source pair.
Do not crop, resize, combine, or recompress the original images.
