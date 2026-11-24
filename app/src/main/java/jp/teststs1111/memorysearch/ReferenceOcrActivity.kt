package jp.teststs1111.memorysearch

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions
import org.json.JSONObject

class ReferenceOcrActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var preview: ReferenceOverlayView
    private var sourceBitmap: Bitmap? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(16, 16, 16, 16)
        }
        status = TextView(this).apply {
            textSize = 14f
            text = "第5章の注釈付き画像をML KitでOCRしています…"
        }
        preview = ReferenceOverlayView(this)
        root.addView(status, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT
        ))
        root.addView(preview, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f
        ))
        setContentView(root)

        try {
            val bitmap = assets.open("annotated.jpg").use { BitmapFactory.decodeStream(it) }
                ?: error("annotated.jpg を読み込めません")
            sourceBitmap = bitmap
            preview.setBitmap(bitmap)
            val candidateJson = assets.open("detected_label_frames.candidates.json")
                .bufferedReader().use { it.readText() }
            val candidates = readCandidates(JSONObject(candidateJson))
            val recognizer = TextRecognition.getClient(JapaneseTextRecognizerOptions.Builder().build())
            recognizer.process(InputImage.fromBitmap(bitmap, 0))
                .addOnSuccessListener { result ->
                    val blocks = result.textBlocks.map { block ->
                        val corners = block.cornerPoints?.map { OcrPoint(it.x, it.y) }
                            ?: block.boundingBox?.let { rect ->
                                listOf(OcrPoint(rect.left, rect.top), OcrPoint(rect.right, rect.top),
                                    OcrPoint(rect.right, rect.bottom), OcrPoint(rect.left, rect.bottom))
                            }.orEmpty()
                        OcrBlockGeometry(block.text, block.lines.map { it.text }, corners)
                    }
                    val names = StageItemCatalogRepository.loadItemNames(assets, "chapter_5")
                    val matches = OcrGeometryMatcher.match(blocks, names)
                    val overlays = matches.mapNotNull { match ->
                        val frame = candidates[match.itemName] ?: return@mapNotNull null
                        ReferenceOverlayView.Pair(match.itemName, frame, match.corners)
                    }
                    preview.setOverlays(overlays)
                    val missing = names.filter { name -> matches.none { it.itemName == name } }
                    status.text = "ML Kit OCR一致：${matches.size}/${names.size}件　枠候補との対応：${overlays.size}件\n" +
                        "緑＝既存の色枠候補／青＝OCR文字の四隅（枠外周ではありません）\n" +
                        if (missing.isEmpty()) "未一致なし" else "OCR未一致：${missing.joinToString("、")}"
                }
                .addOnFailureListener { error ->
                    status.text = "OCR失敗：${error.message ?: "不明"}"
                }
                .addOnCompleteListener { recognizer.close() }
        } catch (error: Exception) {
            status.text = "検証画像を読み込めません：${error.message ?: "不明"}"
        }
    }

    private fun readCandidates(root: JSONObject): Map<String, List<OcrPoint>> {
        val result = LinkedHashMap<String, List<OcrPoint>>()
        val items = root.getJSONArray("items")
        for (index in 0 until items.length()) {
            val item = items.getJSONObject(index)
            if (!item.has("corners")) continue
            val corners = item.getJSONArray("corners")
            if (corners.length() != 4) continue
            result[item.getString("itemName")] = (0 until 4).map { cornerIndex ->
                val point = corners.getJSONArray(cornerIndex)
                OcrPoint((point.getDouble(0) * 1000000).toInt(), (point.getDouble(1) * 1000000).toInt())
            }
        }
        return result
    }

    override fun onDestroy() {
        sourceBitmap?.recycle()
        sourceBitmap = null
        super.onDestroy()
    }
}

private class ReferenceOverlayView(context: android.content.Context) : View(context) {
    data class Pair(val name: String, val normalizedFrame: List<OcrPoint>, val textCorners: List<OcrPoint>)

    private var bitmap: Bitmap? = null
    private var pairs: List<Pair> = emptyList()
    private val imagePaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private val framePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.GREEN
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.CYAN
        style = Paint.Style.STROKE
        strokeWidth = 3f
    }

    fun setBitmap(value: Bitmap) { bitmap = value; invalidate() }
    fun setOverlays(value: List<Pair>) { pairs = value; invalidate() }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val image = bitmap ?: return
        val scale = minOf(width.toFloat() / image.width, height.toFloat() / image.height)
        val left = (width - image.width * scale) / 2f
        val top = (height - image.height * scale) / 2f
        canvas.save()
        canvas.translate(left, top)
        canvas.scale(scale, scale)
        canvas.drawBitmap(image, 0f, 0f, imagePaint)
        pairs.forEach { pair ->
            drawPolygon(canvas, pair.normalizedFrame, image.width.toFloat(), image.height.toFloat(), framePaint)
            drawPolygon(canvas, pair.textCorners, 1f, 1f, textPaint)
        }
        canvas.restore()
    }

    private fun drawPolygon(canvas: Canvas, points: List<OcrPoint>, xScale: Float, yScale: Float, paint: Paint) {
        if (points.size != 4) return
        val path = Path()
        points.forEachIndexed { index, point ->
            val x = if (xScale == 1f) point.x.toFloat() else point.x / 1000000f * xScale
            val y = if (yScale == 1f) point.y.toFloat() else point.y / 1000000f * yScale
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        path.close()
        canvas.drawPath(path, paint)
    }
}
