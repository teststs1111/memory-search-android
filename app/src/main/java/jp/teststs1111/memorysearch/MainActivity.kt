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

        val title = TextView(this).apply {
            text = "記憶探索サポート"
            textSize = 25f
        }
        root.addView(title)

        val subtitle = TextView(this).apply {
            text = "テスト版 0.1.0 — 第1章から対応"
            textSize = 14f
            setPadding(0, padding / 3, 0, padding)
        }
        root.addView(subtitle)

        val stageLabel = TextView(this).apply {
            text = "挑戦するステージ"
            textSize = 18f
        }
        root.addView(stageLabel)

        val stages = listOf("第1章")
        val stageSelector = Spinner(this).apply {
            adapter = ArrayAdapter(
                this@MainActivity,
                android.R.layout.simple_spinner_dropdown_item,
                stages
            )
        }
        root.addView(
            stageSelector,
            LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        )

        val status = TextView(this).apply {
            text = "\n第1章のデータ準備中\n\n次の工程：アイテム座標の登録、画面キャプチャ、文字認識、マーカー表示。\n\n現在は画面とプロジェクトの土台です。座標が未確認のアイテムを誤表示しないよう、認識・マーカー機能はまだ有効にしていません。"
            textSize = 16f
            setPadding(0, padding, 0, 0)
        }
        root.addView(status)

        setContentView(root)
    }
}
