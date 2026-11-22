# Chapter 1 item catalog

Source references:
- `base.jpg`: unannotated Chapter 1 scene.
- `left.jpg`: left-side item-name annotations.
- `right.jpg`: right-side item-name annotations.

This is a transcription of the labels visible in the two annotated references. It is **not** a verified coordinate dataset. Do not use these entries to place markers until each physical object has been matched against `base.jpg` and its normalized center has been checked.

## Left reference

1. マグカップ
2. テディベア
3. 卓上ベル
4. 呼び出しボタン
5. バーコードスキャナー
6. いちごクッション
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
23. 学生証

## Right reference

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
- Reference image size: 414 × 739 pixels for all three source images.
- Coordinate convention: normalized to the game-content rectangle, `x = pixel_x / 414`, `y = pixel_y / 739`.
- Coordinates must refer to the center of the actual target object in `base.jpg`, not the annotation label or the label box.
- Keep `chapter_1.json` as `awaiting_coordinate_verification` with an empty `items` array until all coordinates are checked.
