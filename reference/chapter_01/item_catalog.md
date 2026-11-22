# Chapter 1 item catalog

Source references:
- `base.jpg`: unannotated Chapter 1 scene.
- `left.jpg`: left-side annotated reference.
- `right.jpg`: right-side annotated reference.
- `annotated_pair.jpg`: the two annotated views placed side by side for easier review. The original files remain unchanged.

The names below were checked visually against the actual uploaded annotation images. This catalog is a name list, not a verified target-object coordinate dataset. The current task is to highlight each item's **name label frame** as a rectangle; the frame coordinates are stored separately as review-only candidates.

## Left reference (24 items)

1. マグカップ
2. テディベア
3. 呼び出しボタン
4. バーコードスキャナー
5. いちごクッション
6. 卓上ベル
7. カップケーキ
8. おにぎり
9. 売り切れプレート
10. トレー
11. ロールケーキ
12. マカロン
13. ラッピングリボン
14. いちごプリン
15. アイリスメガネ
16. 黒いリボン
17. ピンクのカゴ
18. レシート
19. ハンカチ
20. いちごスプーン
21. プリンのスタンプ
22. ハートのティッシュ
23. ポイントカード
24. 学生証

## Right reference (8 items)

1. プリンの張り紙
2. プリンのぬいぐるみ
3. コーヒー牛乳
4. いちごオレ
5. 牛乳
6. イチゴジャム
7. ドーナツボックス
8. ゴールドスプーン

## Coordinate verification

- Status: pending.
- The original images are kept unchanged.
- The 32 name-label rectangles are mapped to `base.jpg` and stored in `app/src/main/assets/stages/chapter_1_label_boxes.candidates.json`.
- The candidate rectangles are normalized to the base image and are intended to outline the entire label frame, not the target object.
- The combined annotated sheet is a visual aid only; it is not a coordinate reference.
- Keep `chapter_1.json` as `awaiting_coordinate_verification` with an empty `items` array; label-frame candidates must remain separate from physical-object coordinates.
