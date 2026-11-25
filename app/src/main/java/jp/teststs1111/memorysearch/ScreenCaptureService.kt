package jp.teststs1111.memorysearch

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.Point
import org.json.JSONArray
import org.json.JSONObject
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.SystemClock
import android.os.IBinder
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions

/**
 * One-shot, in-memory screen capture and Japanese OCR.
 * The captured bitmap is never written to storage or transmitted.
 */
class ScreenCaptureService : Service() {
    private var projection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var worker: HandlerThread? = null
    @Volatile private var stopped = false
    private var frameHandled = false
    @Volatile private var continuousMode = false
    @Volatile private var ocrInFlight = false
    private var lastOcrStartedAt = 0L
    private var recognizer: com.google.mlkit.vision.text.TextRecognizer? = null
    private val targetSetTracker = TargetSetTransitionTracker()
    private var requestedStageId: String = "chapter_1"

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP_CAPTURE) {
            stopCapture()
            return START_NOT_STICKY
        }
        continuousMode = intent?.getBooleanExtra(EXTRA_CONTINUOUS, false) == true
        createNotificationChannel()
        val notification = Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("記憶探索サポート")
            .setContentText(if (continuousMode) "画面を継続確認中（停止するまで動作）" else "画面取得・日本語OCRテストを実行中")
            .setSmallIcon(android.R.drawable.ic_menu_view)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        requestedStageId = intent?.getStringExtra(EXTRA_STAGE_ID)?.takeIf { it.matches(Regex("chapter_[0-9]+")) } ?: "chapter_1"
        val resultCode = intent?.getIntExtra(EXTRA_RESULT_CODE, 0) ?: 0
        val resultData = if (Build.VERSION.SDK_INT >= 33) {
            intent?.getParcelableExtra(EXTRA_RESULT_DATA, Intent::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent?.getParcelableExtra(EXTRA_RESULT_DATA)
        }
        if (resultCode == 0 || resultData == null) {
            reportFailure("画面取得の許可情報を受け取れませんでした")
            stopCapture()
            return START_NOT_STICKY
        }

        try {
            val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            projection = manager.getMediaProjection(resultCode, resultData)
            projection?.registerCallback(object : MediaProjection.Callback() {
                override fun onStop() {
                    stopCapture()
                }
            }, Handler(mainLooper))

            val metrics = resources.displayMetrics
            val width = metrics.widthPixels.coerceAtLeast(1)
            val height = metrics.heightPixels.coerceAtLeast(1)
            val density = metrics.densityDpi

            worker = HandlerThread("screen-capture-ocr").also { it.start() }
            val handler = Handler(worker!!.looper)
            imageReader = ImageReader.newInstance(width, height, android.graphics.PixelFormat.RGBA_8888, 2)
            recognizer = TextRecognition.getClient(JapaneseTextRecognizerOptions.Builder().build())
            imageReader?.setOnImageAvailableListener({ reader ->
                val image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
                if (continuousMode) {
                    val now = SystemClock.elapsedRealtime()
                    if (ocrInFlight || now - lastOcrStartedAt < MIN_OCR_INTERVAL_MS) {
                        image.close()
                        return@setOnImageAvailableListener
                    }
                    lastOcrStartedAt = now
                } else {
                    if (frameHandled) {
                        image.close()
                        return@setOnImageAvailableListener
                    }
                    frameHandled = true
                }
                val bitmap = try {
                    imageToBitmap(image)
                } catch (error: Exception) {
                    image.close()
                    reportFailure("画像のメモリ変換に失敗しました：${error.message ?: "不明"}")
                    stopCapture()
                    return@setOnImageAvailableListener
                }
                image.close()
                ocrInFlight = true
                runJapaneseOcr(bitmap)
            }, handler)

            virtualDisplay = projection?.createVirtualDisplay(
                if (continuousMode) "MemorySearchContinuous" else "MemorySearchOneShot",
                width,
                height,
                density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader?.surface,
                null,
                handler
            )
        } catch (error: Exception) {
            reportFailure(error.message ?: "画面取得に失敗しました")
            stopCapture()
        }
        return START_NOT_STICKY
    }

    private fun imageToBitmap(image: Image): Bitmap {
        val plane = image.planes[0]
        val pixelStride = plane.pixelStride
        val rowStride = plane.rowStride
        val rowBytes = image.width * pixelStride
        val source = plane.buffer
        val compact = java.nio.ByteBuffer.allocate(image.width * image.height * 4)
        val row = ByteArray(rowBytes)
        for (y in 0 until image.height) {
            source.position(y * rowStride)
            source.get(row, 0, rowBytes)
            compact.put(row)
        }
        compact.rewind()
        return Bitmap.createBitmap(image.width, image.height, Bitmap.Config.ARGB_8888).apply {
            copyPixelsFromBuffer(compact)
        }
    }

    private fun runJapaneseOcr(bitmap: Bitmap) {
        try {
            val activeRecognizer = recognizer ?: throw IllegalStateException("OCRエンジンが初期化されていません")
            activeRecognizer.process(InputImage.fromBitmap(bitmap, 0))
                .addOnSuccessListener { result ->
                    val blocks = result.textBlocks.map { block -> block.lines.map { line -> line.text } }
                    val lines = blocks.flatten()
                    val itemNames = StageItemCatalogRepository.loadItemNames(assets, requestedStageId)
                    val geometryBlocks = result.textBlocks.map { block ->
                        val corners = block.cornerPoints?.map { point -> OcrPoint(point.x, point.y) }
                            ?: block.boundingBox?.let { rect ->
                                listOf(
                                    OcrPoint(rect.left, rect.top),
                                    OcrPoint(rect.right, rect.top),
                                    OcrPoint(rect.right, rect.bottom),
                                    OcrPoint(rect.left, rect.bottom)
                                )
                            }.orEmpty()
                        OcrBlockGeometry(block.text, block.lines.map { it.text }, corners)
                    }
                    // Preserve each raw ML Kit block and its four corners for on-device diagnosis.
                    // This lets us distinguish OCR segmentation failures from geometry-matching failures.
                    val blockGeometryJson = ArrayList(geometryBlocks.mapIndexed { index, block ->
                        JSONObject()
                            .put("index", index)
                            .put("text", block.text)
                            .put("lines", JSONArray(block.lines))
                            .put("corners", JSONArray().apply {
                                block.corners.forEach { point ->
                                    put(JSONObject().put("x", point.x).put("y", point.y))
                                }
                            })
                            .toString()
                    })
                    val twoLinePatterns = TwoLineOcrPatterns.forStage(requestedStageId)
                    // Keep full-screen geometry for board-label diagnostics, but derive the
                    // three live targets only from the shared bottom target-button strip.
                    val locatedItems = OcrGeometryMatcher.match(geometryBlocks, itemNames, twoLinePatterns)
                    val targetStripBlocks = TargetStripRegion.filter(geometryBlocks, bitmap.width, bitmap.height)
                    val targetStripBlockMatches = OcrItemMatcher.matchBlocks(
                        targetStripBlocks.map { it.lines },
                        itemNames,
                        twoLinePatterns
                    ).toSet()
                    val targetStripLocatedNames = OcrGeometryMatcher.match(
                        targetStripBlocks,
                        itemNames,
                        twoLinePatterns
                    ).map { it.itemName }.toSet()
                    val targetStripMatches = itemNames.filter {
                        it in targetStripBlockMatches || it in targetStripLocatedNames
                    }
                    val targetUpdate = if (continuousMode) targetSetTracker.observe(targetStripMatches) else null
                    val locatedJson = ArrayList(locatedItems.map { item ->
                        JSONObject()
                            .put("itemName", item.itemName)
                            .put("recognizedText", item.recognizedText)
                            .put("corners", JSONArray().apply {
                                item.corners.forEach { point ->
                                    put(JSONObject().put("x", point.x).put("y", point.y))
                                }
                            })
                            .toString()
                    })
                    sendBroadcast(Intent(ACTION_OCR_RESULT).setPackage(packageName).apply {
                        putExtra(EXTRA_WIDTH, bitmap.width)
                        putExtra(EXTRA_HEIGHT, bitmap.height)
                        putExtra(EXTRA_STAGE_ID, requestedStageId)
                        putExtra(EXTRA_CONTINUOUS, continuousMode)
                        putStringArrayListExtra(EXTRA_TARGET_STRIP_MATCHES, ArrayList(targetStripMatches))
                        targetUpdate?.let { update ->
                            putStringArrayListExtra(EXTRA_ACTIVE_TARGETS, ArrayList(update.activeTargets))
                            putExtra(EXTRA_TARGET_SET_CHANGED, update.changed)
                        }
                        putExtra(EXTRA_OCR_TEXT, result.text)
                        putStringArrayListExtra(EXTRA_OCR_LINES, ArrayList(lines))
                        // Keep OCR block boundaries so separate labels are never joined.
                        putStringArrayListExtra(EXTRA_OCR_BLOCKS, ArrayList(blocks.map { it.joinToString("\n") }))
                        putStringArrayListExtra(EXTRA_OCR_BLOCK_GEOMETRY, blockGeometryJson)
                        // Exact catalog matches retain ML Kit's original four-corner geometry.
                        putStringArrayListExtra(EXTRA_OCR_LOCATED_ITEMS, locatedJson)
                    })
                }
                .addOnFailureListener { error ->
                    reportFailure("日本語OCRに失敗しました：${error.message ?: "不明"}")
                }
                .addOnCompleteListener {
                    if (!bitmap.isRecycled) bitmap.recycle()
                    ocrInFlight = false
                    if (stopped) {
                        recognizer?.close()
                        recognizer = null
                    } else if (!continuousMode) {
                        stopCapture()
                    }
                }
        } catch (error: Exception) {
            // ML Kit setup or task submission can fail before async listeners run.
            if (!bitmap.isRecycled) bitmap.recycle()
            ocrInFlight = false
            if (stopped) {
                recognizer?.close()
                recognizer = null
            }
            reportFailure("日本語OCRを開始できませんでした：${error.message ?: "不明"}")
            if (!continuousMode && !stopped) stopCapture()
        }
    }

    private fun reportFailure(message: String) {
        sendBroadcast(Intent(ACTION_CAPTURE_ERROR).setPackage(packageName).putExtra(EXTRA_ERROR, message))
    }

    @Synchronized
    private fun stopCapture() {
        if (stopped) return
        stopped = true
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.setOnImageAvailableListener(null, null)
        imageReader?.close()
        imageReader = null
        projection?.stop()
        projection = null
        // ML Kit may still be using the recognizer; close it after its task completes.
        if (!ocrInFlight) {
            recognizer?.close()
            recognizer = null
        }
        worker?.quitSafely()
        worker = null
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, "画面取得・OCRテスト", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    companion object {
        const val ACTION_CAPTURE_RESULT = "jp.teststs1111.memorysearch.CAPTURE_RESULT"
        const val ACTION_CAPTURE_ERROR = "jp.teststs1111.memorysearch.CAPTURE_ERROR"
        const val ACTION_OCR_RESULT = "jp.teststs1111.memorysearch.OCR_RESULT"
        const val ACTION_STOP_CAPTURE = "jp.teststs1111.memorysearch.STOP_CAPTURE"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        const val EXTRA_WIDTH = "frame_width"
        const val EXTRA_HEIGHT = "frame_height"
        const val EXTRA_OCR_TEXT = "ocr_text"
        const val EXTRA_OCR_LINES = "ocr_lines"
        const val EXTRA_OCR_BLOCKS = "ocr_blocks"
        const val EXTRA_OCR_BLOCK_GEOMETRY = "ocr_block_geometry"
        const val EXTRA_OCR_LOCATED_ITEMS = "ocr_located_items"
        const val EXTRA_STAGE_ID = "stage_id"
        const val EXTRA_CONTINUOUS = "continuous_capture"
        const val EXTRA_ACTIVE_TARGETS = "active_targets"
        const val EXTRA_TARGET_STRIP_MATCHES = "target_strip_matches"
        const val EXTRA_TARGET_SET_CHANGED = "target_set_changed"
        const val EXTRA_ERROR = "error"
        private const val CHANNEL_ID = "screen_capture_test"
        private const val NOTIFICATION_ID = 41
        private const val MIN_OCR_INTERVAL_MS = 200L
    }
}
