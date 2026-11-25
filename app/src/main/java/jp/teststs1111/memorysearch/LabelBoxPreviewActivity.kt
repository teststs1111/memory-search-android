package jp.teststs1111.memorysearch

import android.app.Activity
import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView

class LabelBoxPreviewActivity : Activity() {
    companion object {
        const val EXTRA_STAGE_ID = "jp.teststs1111.memorysearch.EXTRA_STAGE_ID"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val stageId = intent.getStringExtra(EXTRA_STAGE_ID) ?: "chapter_1"
        require(stageId.matches(Regex("chapter_[0-9]+"))) { "Invalid stage ID: $stageId" }
        val chapterNumber = stageId.substringAfter('_')
        val padding = (12 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
        }
        root.addView(TextView(this).apply {
            text = "第${chapterNumber}章・名称枠座標プレビュー"
            textSize = 20f
        })
        root.addView(TextView(this).apply {
            text = "黄色い枠は座標候補です。実プレイには反映されません。画像内の枠との位置ずれ・欠落を確認するための画面です。"
            textSize = 13f
            setPadding(0, padding / 2, 0, padding)
        })

        try {
            val dataset = StageLabelBoxRepository.loadCandidatesForStage(assets, stageId)
            val bitmap = assets.open("base.jpg").use { input ->
                BitmapFactory.decodeStream(input)
            } ?: error("基準画像を読み込めません")
            root.addView(TextView(this).apply {
                text = "座標候補：${dataset.items.size}件 / 実行時有効：${StageLabelBoxValidator.activeBoxes(dataset).size}件"
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
                text = "座標プレビューを読み込めませんでした。\n${error.message ?: "画像または候補データを確認してください。"}"
                textSize = 15f
            })
        }
        setContentView(root)
    }
}
