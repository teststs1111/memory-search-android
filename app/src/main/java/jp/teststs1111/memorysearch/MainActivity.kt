package jp.teststs1111.memorysearch

import android.app.Activity
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val padding = (20 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(padding, padding, padding, padding)
            gravity = Gravity.TOP
        }

        root.addView(TextView(this).apply {
            text = "記憶探索サポート"
            textSize = 25f
        })
        root.addView(TextView(this).apply {
            text = "テスト版 ${packageManager.getPackageInfo(packageName, 0).versionName ?: "不明"} — 第1章データ読込対応"
            textSize = 14f
            setPadding(0, padding / 3, 0, padding)
        })
        root.addView(TextView(this).apply {
            text = "挑戦するステージ"
            textSize = 18f
        })

        val status = TextView(this).apply {
            textSize = 16f
            setPadding(0, padding, 0, 0)
        }
        root.addView(status)

        try {
            val stages = StageDatasetRepository.loadStages(assets)
            if (stages.isEmpty()) {
                status.text = "ステージデータがありません。"
            } else {
                val selector = Spinner(this).apply {
                    adapter = ArrayAdapter(
                        this@MainActivity,
                        android.R.layout.simple_spinner_dropdown_item,
                        stages.map { it.stageName }
                    )
                }
                root.addView(
                    selector,
                    LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                    )
                )

                fun updateStatus(index: Int) {
                    val stage = stages[index]
                    val dataMessage = if (stage.dataStatus == "verified") {
                        "確認済みアイテム：${stage.items.size}件"
                    } else {
                        "座標確認待ち：登録アイテム ${stage.items.size}件（マーカー表示対象外）"
                    }
                    status.text = "\n${stage.stageName}\n${dataMessage}\n\n現在はステージデータの読み込みと検証まで対応しています。ゲーム画面のキャプチャ、OCR、マーカー表示はまだ行いません。"
                }
                selector.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
                    override fun onItemSelected(
                        parent: android.widget.AdapterView<*>?,
                        view: android.view.View?,
                        position: Int,
                        id: Long
                    ) = updateStatus(position)

                    override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
                }
                updateStatus(0)
            }
        } catch (error: Exception) {
            status.text = "ステージデータを読み込めませんでした。\n${error.message ?: "データ形式を確認してください。"}"
        }

        setContentView(root)
    }
}
