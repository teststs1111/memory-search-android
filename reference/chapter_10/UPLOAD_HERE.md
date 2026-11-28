Chapter 10 original reference pair was located and downloaded unchanged from the atwiki attachments.

- Annotated source: https://img.atwiki.jp/eden_jp/attach/46/157/%E7%AC%AC10%E7%AB%A0.jpeg
  - 2016×2520 JPEG
  - SHA-256: c10ffa2a046edbe6bb0b948d3a4ad27fbb3ca48fbc0898dba8709971fcc199ac
- Clean base: https://img.atwiki.jp/eden_jp/attach/46/158/%E7%AC%AC10%E7%AB%A0%E7%84%A1%E5%8A%A0%E5%B7%A5.jpeg
  - 1404×2496 JPEG
  - SHA-256: a7596c060e330d5f69b3e079a5218a00487b6b83747bfdef94d634b4a453cc55

The images are not the same dimensions. The annotated image was aligned to the clean base using SIFT feature matching and a RANSAC homography (3302 good matches, 3244 inliers, 0.982435 inlier ratio). Candidate rectangles were traced on the annotated source and mapped to the established 563×1000 coordinate basis. The source images are never resized, recompressed, or committed as transformed replacements; the review workflow downloads the originals, checks hashes/dimensions, and uploads the comparison as an artifact.

Candidate review status: 30 complete visible boxes, three edge-clipped boxes (トランシーバー, ロープ, レンチ), one near-edge mapping (木片), and one catalog item with no distinct annotation backing (バケツ). 青いバケツ is visibly split into the two reference lines バケツ / 青. These are candidate-only coordinates and are not enabled at runtime.

Do not infer missing boundaries or promote the pending items without a fuller reference. Live bottom-button OCR remains single-line; no per-play coordinate detection is introduced.
