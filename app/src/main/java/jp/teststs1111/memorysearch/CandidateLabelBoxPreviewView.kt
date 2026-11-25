package jp.teststs1111.memorysearch

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.View

/** Displays candidate rectangles for manual inspection only; never used by runtime highlighting. */
class CandidateLabelBoxPreviewView(
    context: Context,
    private val bitmap: Bitmap,
    private val candidates: List<StageLabelBox>
) : View(context) {
    private val density = resources.displayMetrics.density
    private var highlightedItemNames: Set<String> = emptySet()
    private val imagePaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val outlinePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(255, 220, 40)
        style = Paint.Style.STROKE
        strokeWidth = 2f * density
    }
    private val glowPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.CYAN
        style = Paint.Style.STROKE
        strokeWidth = 8f * density
    }
    private val highlightPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(80, 255, 255)
        style = Paint.Style.STROKE
        strokeWidth = 3.5f * density
    }
    private val markerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(220, 20, 20, 20)
        style = Paint.Style.FILL
    }
    private val numberPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textAlign = Paint.Align.CENTER
        textSize = 10f * density
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }

    init {
        // setShadowLayer requires a software canvas; this is confined to the preview screen.
        setLayerType(LAYER_TYPE_SOFTWARE, null)
    }

    fun setHighlightedItemNames(names: Collection<String>) {
        highlightedItemNames = names.filter { it.isNotBlank() }.toSet()
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width <= 0 || height <= 0) return

        val scale = minOf(width.toFloat() / bitmap.width, height.toFloat() / bitmap.height)
        val drawWidth = bitmap.width * scale
        val drawHeight = bitmap.height * scale
        val offsetX = (width - drawWidth) / 2f
        val offsetY = (height - drawHeight) / 2f
        val destination = RectF(offsetX, offsetY, offsetX + drawWidth, offsetY + drawHeight)
        canvas.drawColor(Color.rgb(35, 35, 35))
        canvas.drawBitmap(bitmap, null, destination, imagePaint)

        candidates.forEachIndexed { index, item ->
            val bounds = item.bounds
            val rect = RectF(
                offsetX + bounds.left.toFloat() * drawWidth,
                offsetY + bounds.top.toFloat() * drawHeight,
                offsetX + bounds.right.toFloat() * drawWidth,
                offsetY + bounds.bottom.toFloat() * drawHeight
            )
            val isHighlighted = LabelHighlightSelection.isTarget(item.itemName, highlightedItemNames)
            if (isHighlighted) {
                glowPaint.setShadowLayer(12f * density, 0f, 0f, Color.CYAN)
                canvas.drawRect(rect, glowPaint)
                canvas.drawRect(rect, highlightPaint)
            } else {
                canvas.drawRect(rect, outlinePaint)
            }
            val radius = 9f * density
            val markerX = (rect.left + radius).coerceIn(offsetX + radius, offsetX + drawWidth - radius)
            val markerY = (rect.top + radius).coerceIn(offsetY + radius, offsetY + drawHeight - radius)
            canvas.drawCircle(markerX, markerY, radius, markerPaint)
            canvas.drawText((index + 1).toString(), markerX, markerY + 3.5f * density, numberPaint)
        }
    }
}
