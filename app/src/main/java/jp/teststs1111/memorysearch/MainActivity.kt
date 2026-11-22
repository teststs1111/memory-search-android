package jp.teststs1111.memorysearch

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var captureStatus: TextView
    private var receiverRegistered = false
    private var selectedStageId: String = "chapter_1"

    private val captureReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                ScreenCaptureService.ACTION_CAPTURE_RESULT -> {
                    val width = intent.getIntExtra(ScreenCaptureService.EXTRA_WIDTH, 0)
                    val height = intent.getIntExtra(ScreenCaptureService.EXTRA_HEIGHT, 0)
                    captureStatus.text = "画面取得成功：${width} × ${height} px"
                }
                ScreenCaptureService.ACTION_OCR_RESULT -> {
                    val width = intent.getIntExtra(ScreenCaptureService.EXTRA_WIDTH, 0)
                    val height = intent.getIntExtra(ScreenCaptureService.EXTRA_HEIGHT, 0)
                    val lines = intent.getStringArrayListExtra(ScreenCaptureService.EXTRA_OCR_LINES).orEmpty()
                    val itemNames = StageLabelBoxRepository.loadCandidateItemNames(assets, selectedStageId)
                    val matches = OcrItemMatcher.matchLines(lines, itemNames)
                    val matchText = if (matches.isEmpty()) {
                        "選択中の章のアイテム名との完全一致はありません。"
                    } else {
                        "一致したアイテム：\\n" + matches.joinToString("、")
                    }
                    val recognized = lines.joinToString("\\n").ifBlank { "文字を検出できませんでした。" }
                    captureStatus.text = "画面取得・日本語OCR成功：${width} × ${height} px\\n章：${selectedStageId}\\n\\n${matchText}\\n\\nOCR行：\\n${recognized.take(1200)}\\n\\n画像は保存せず、メモリ上で破棄しました。枠座標は未検証のため光りません。"
                }
                ScreenCaptureService.ACTION_CAPTURE_ERROR -> {
                    captureStatus.text = "画面取得/OCRエラー：${intent.getStringExtra(ScreenCaptureService.EXTRA_ERROR) ?: "不明"}"
                }
            }
        }
    }

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
            text = "テスト版 ${packageManager.getPackageInfo(packageName, 0).versionName ?: "不明"} — 全10章データ読込対応"
            textSize = 14f
            setPadding(0, padding / 3, 0, padding)
        })
        root.addView(TextView(this).apply {
            text = "挑戦するステージ"
            textSize = 18f
        })
        val stageStatus = TextView(this).apply {
            textSize = 16f
            setPadding(0, padding, 0, 0)
        }
        root.addView(stageStatus)
        try {
            val stages = StageDatasetRepository.loadStages(assets)
            if (stages.isEmpty()) {
                stageStatus.text = "ステージデータがありません。"
            } else {
                val selector = Spinner(this).apply {
                    adapter = ArrayAdapter(this@MainActivity, android.R.layout.simple_spinner_dropdown_item, stages.map { it.stageName })
                }
                root.addView(selector, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
                fun updateStatus(index: Int) {
                    val stage = stages[index]
                    selectedStageId = stage.stageId
                    val message = if (stage.dataStatus == "verified") {
                        "確認済みアイテム：${stage.items.size}件"
                    } else {
                        "座標確認待ち：登録アイテム ${stage.items.size}件（マーカー表示対象外）"
                    }
                    stageStatus.text = "\n${stage.stageName}\n${message}\n\n名称枠プレビューは確認専用です。番号は実プレイ画面には表示しません。"
                }
                selector.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
                    override fun onItemSelected(parent: android.widget.AdapterView<*>?, view: android.view.View?, position: Int, id: Long) = updateStatus(position)
                    override fun onNothingSelected(parent: android.widget.AdapterView<*>?) = Unit
                }
                updateStatus(0)
                root.addView(Button(this).apply {
                    text = "第1章の名称枠プレビュー（候補）"
                    setOnClickListener { startActivity(Intent(this@MainActivity, LabelBoxPreviewActivity::class.java)) }
                })
            }
        } catch (error: Exception) {
            stageStatus.text = "ステージデータを読み込めませんでした。\n${error.message ?: "データ形式を確認してください。"}"
        }

        root.addView(TextView(this).apply {
            text = "画面取得・日本語OCRテスト"
            textSize = 18f
            setPadding(0, padding, 0, 0)
        })
        captureStatus = TextView(this).apply {
            text = "許可を求めたときだけ1フレームを取得して日本語OCRを行います。画像は保存しません。"
            textSize = 14f
            setPadding(0, padding / 2, 0, padding / 2)
        }
        root.addView(captureStatus)
        root.addView(Button(this).apply {
            text = "画面取得・日本語OCRテスト"
            setOnClickListener {
                val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                @Suppress("DEPRECATION")
                startActivityForResult(manager.createScreenCaptureIntent(), REQUEST_CAPTURE)
            }
        })
        setContentView(root)
    }

    override fun onStart() {
        super.onStart()
        if (!receiverRegistered) {
            val filter = IntentFilter().apply {
                addAction(ScreenCaptureService.ACTION_CAPTURE_RESULT)
                addAction(ScreenCaptureService.ACTION_CAPTURE_ERROR)
                addAction(ScreenCaptureService.ACTION_OCR_RESULT)
            }
            if (Build.VERSION.SDK_INT >= 33) {
                registerReceiver(captureReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
            } else {
                @Suppress("DEPRECATION")
                registerReceiver(captureReceiver, filter)
            }
            receiverRegistered = true
        }
    }

    override fun onStop() {
        if (receiverRegistered) {
            unregisterReceiver(captureReceiver)
            receiverRegistered = false
        }
        super.onStop()
    }

    @Deprecated("Uses the platform permission result callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == REQUEST_CAPTURE) {
            if (resultCode == RESULT_OK && data != null) {
                captureStatus.text = "許可を受け取りました。1フレームを取得して日本語OCRを実行します…"
                val serviceIntent = Intent(this, ScreenCaptureService::class.java).apply {
                    putExtra(ScreenCaptureService.EXTRA_RESULT_CODE, resultCode)
                    putExtra(ScreenCaptureService.EXTRA_RESULT_DATA, data)
                    putExtra(ScreenCaptureService.EXTRA_STAGE_ID, selectedStageId)
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(serviceIntent) else startService(serviceIntent)
            } else {
                captureStatus.text = "画面取得はキャンセルされました。ゲームには影響ありません。"
            }
        }
    }

    companion object {
        private const val REQUEST_CAPTURE = 5101
    }
}
