package jp.teststs1111.memorysearch

import android.app.Activity
import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView

class LabelBoxPreviewActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val padding = (12 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }
        root.addView(TextView(this).apply {
            text = "第1章・名称枠プレビュー"
            textSize = 20f
        })
        root.addView(TextView(this).apply {
            text = "黄色い枠は確認用の候補です。ゲーム画面には表示されず、タッチ操作にも影響しません。"
            textSize = 13f
            setPadding(0, padding / 2, 0, padding)
        })

        try {
            val dataset = StageLabelBoxRepository.loadChapterOneCandidates(assets)
            val bitmap = assets.open("base.jpg").use { input ->
                BitmapFactory.decodeStream(input)
            } ?: error("基準画像を読み込めません")
            root.addView(TextView(this).apply {
                text = "候補枠：${dataset.items.size}件 / 実行時有効：${StageLabelBoxValidator.activeBoxes(dataset).size}件"
                textSize = 13f
                setPadding(0, 0, 0, padding / 2)
            })
            root.addView(
                CandidateLabelBoxPreviewView(this, bitmap, dataset.items),
                LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    0,
                    1f
                )
            )
        } catch (error: Exception) {
            root.addView(TextView(this).apply {
                text = "プレビューを読み込めませんでした。\n${error.message ?: "画像または候補データを確認してください。"}"
                textSize = 15f
            })
        }
        setContentView(root)
    }
}
