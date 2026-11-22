package jp.teststs1111.memorysearch

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder

/**
 * One-shot, in-memory screen capture smoke test.
 * Captures only the first frame dimensions; pixels are never saved or transmitted.
 */
class ScreenCaptureService : Service() {
    private var projection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var worker: HandlerThread? = null
    private var stopped = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        createNotificationChannel()
        val notification = Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("記憶探索サポート")
            .setContentText("画面取得テストを実行中")
            .setSmallIcon(android.R.drawable.ic_menu_view)
            .setOngoing(true)
            .build()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

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

            worker = HandlerThread("screen-capture").also { it.start() }
            val handler = Handler(worker!!.looper)
            imageReader = ImageReader.newInstance(width, height, android.graphics.PixelFormat.RGBA_8888, 2)
            imageReader?.setOnImageAvailableListener({ reader ->
                val image = reader.acquireLatestImage()
                if (image != null) {
                    val frameWidth = image.width
                    val frameHeight = image.height
                    image.close()
                    sendBroadcast(Intent(ACTION_CAPTURE_RESULT).setPackage(packageName).apply {
                        putExtra(EXTRA_WIDTH, frameWidth)
                        putExtra(EXTRA_HEIGHT, frameHeight)
                    })
                    stopCapture()
                }
            }, handler)

            virtualDisplay = projection?.createVirtualDisplay(
                "MemorySearchOneShot",
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

    private fun reportFailure(message: String) {
        sendBroadcast(Intent(ACTION_CAPTURE_ERROR).setPackage(packageName).putExtra(EXTRA_ERROR, message))
    }

    private fun stopCapture() {
        if (stopped) return
        stopped = true
        virtualDisplay?.release()
        virtualDisplay = null
        imageReader?.close()
        imageReader = null
        projection?.stop()
        projection = null
        worker?.quitSafely()
        worker = null
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, "画面取得テスト", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    companion object {
        const val ACTION_CAPTURE_RESULT = "jp.teststs1111.memorysearch.CAPTURE_RESULT"
        const val ACTION_CAPTURE_ERROR = "jp.teststs1111.memorysearch.CAPTURE_ERROR"
        const val EXTRA_RESULT_CODE = "result_code"
        const val EXTRA_RESULT_DATA = "result_data"
        const val EXTRA_WIDTH = "frame_width"
        const val EXTRA_HEIGHT = "frame_height"
        const val EXTRA_ERROR = "error"
        private const val CHANNEL_ID = "screen_capture_test"
        private const val NOTIFICATION_ID = 41
    }
}
