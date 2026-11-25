package jp.teststs1111.memorysearch

import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.PixelFormat
import android.graphics.RectF
import android.os.Build
import android.os.IBinder
import android.view.Gravity
import android.view.View
import android.view.WindowManager

/**
 * Click-through overlay. Marker positions come only from the verified stage dataset;
 * OCR is used only to identify the three target names.
 */
class HighlightOverlayService : Service() {
    private var windowManager: WindowManager? = null
    private var overlayView: HighlightView? = null
    private var dataset: StageDataset? = null
    private var receiverRegistered = false

    private val ocrReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != ScreenCaptureService.ACTION_OCR_RESULT) return
            val resultStageId = intent.getStringExtra(ScreenCaptureService.EXTRA_STAGE_ID) ?: return
            if (resultStageId != dataset?.stageId) return
            val activeNames = intent.getStringArrayListExtra(ScreenCaptureService.EXTRA_ACTIVE_TARGETS).orEmpty()
            val resolved = StageTargetResolver.resolve(dataset ?: return, activeNames)
            overlayView?.setHighlightedItems(resolved)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP_OVERLAY) {
            stopSelf()
            return START_NOT_STICKY
        }
        val stageId = intent?.getStringExtra(EXTRA_STAGE_ID)
            ?.takeIf { it.matches(Regex("chapter_[0-9]+")) } ?: "chapter_5"
        return try {
            dataset = StageDatasetRepository.loadStages(assets).firstOrNull { it.stageId == stageId }
                ?: error("ステージ座標が見つかりません")
            check(StageDatasetValidator.markerItems(dataset!!).isNotEmpty()) {
                "このステージの座標はまだ確認されていません"
            }
            if (overlayView == null) attachOverlay()
            if (!receiverRegistered) {
                val filter = IntentFilter(ScreenCaptureService.ACTION_OCR_RESULT)
                if (Build.VERSION.SDK_INT >= 33) {
                    registerReceiver(ocrReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
                } else {
                    @Suppress("DEPRECATION")
                    registerReceiver(ocrReceiver, filter)
                }
                receiverRegistered = true
            }
            START_NOT_STICKY
        } catch (error: Exception) {
            stopSelf()
            START_NOT_STICKY
        }
    }

    private fun attachOverlay() {
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val view = HighlightView(this) { dataset }
        val windowType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            windowType,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply { gravity = Gravity.TOP or Gravity.START }
        windowManager?.addView(view, params)
        overlayView = view
    }

    override fun onDestroy() {
        if (receiverRegistered) {
            runCatching { unregisterReceiver(ocrReceiver) }
            receiverRegistered = false
        }
        overlayView?.let { view -> runCatching { windowManager?.removeView(view) } }
        overlayView = null
        windowManager = null
        super.onDestroy()
    }

    companion object {
        const val ACTION_STOP_OVERLAY = "jp.teststs1111.memorysearch.STOP_HIGHLIGHT_OVERLAY"
        const val EXTRA_STAGE_ID = "jp.teststs1111.memorysearch.OVERLAY_STAGE_ID"
    }
}

private class HighlightView(
    context: Context,
    private val currentDataset: () -> StageDataset?
) : View(context) {
    private var highlightedItems: List<StageItem> = emptyList()
    private val density = resources.displayMetrics.density
    private val glow = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.CYAN
        style = Paint.Style.STROKE
        strokeWidth = 5f * density
    }
    private val inner = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.STROKE
        strokeWidth = 1.7f * density
    }

    init {
        setLayerType(LAYER_TYPE_SOFTWARE, null)
        importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO
    }

    fun setHighlightedItems(items: List<StageItem>) {
        highlightedItems = items
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val dataset = currentDataset() ?: return
        if (width <= 0 || height <= 0) return

        // Chapter 5 reference image is 563×1000. Keep its content rectangle stable;
        // no board or label coordinates are detected from the live game screen.
        val sourceWidth = 563
        val sourceHeight = 1000
        val scale = minOf(width.toFloat() / sourceWidth, height.toFloat() / sourceHeight)
        val contentWidth = sourceWidth * scale
        val contentHeight = sourceHeight * scale
        val offsetX = (width - contentWidth) / 2f
        val offsetY = (height - contentHeight) / 2f

        highlightedItems.forEach { item ->
            val left = offsetX + ((item.x - item.width / 2.0) * contentWidth).toFloat()
            val top = offsetY + ((item.y - item.height / 2.0) * contentHeight).toFloat()
            val right = offsetX + ((item.x + item.width / 2.0) * contentWidth).toFloat()
            val bottom = offsetY + ((item.y + item.height / 2.0) * contentHeight).toFloat()
            val rect = RectF(left, top, right, bottom)
            glow.setShadowLayer(15f * density, 0f, 0f, Color.CYAN)
            canvas.drawRoundRect(rect, 8f * density, 8f * density, glow)
            canvas.drawRoundRect(rect, 8f * density, 8f * density, inner)
        }
    }
}
