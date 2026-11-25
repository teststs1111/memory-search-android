package jp.teststs1111.memorysearch

import android.graphics.BitmapFactory
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.util.concurrent.TimeUnit
import com.google.android.gms.tasks.Tasks

@RunWith(AndroidJUnit4::class)
class Chapter5ReferenceOcrInstrumentedTest {
    @Test
    fun mlKitRecognizesBothTwoLineLabelsFromOriginalReferenceImage() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val bitmap = context.assets.open("annotated.jpg").use { stream ->
            requireNotNull(BitmapFactory.decodeStream(stream)) { "annotated.jpg could not be decoded" }
        }
        val recognizer = TextRecognition.getClient(JapaneseTextRecognizerOptions.Builder().build())

        try {
            val result = Tasks.await(
                recognizer.process(InputImage.fromBitmap(bitmap, 0)),
                300,
                TimeUnit.SECONDS
            )
            val blocks = result.textBlocks.map { block ->
                val corners = block.cornerPoints?.map { OcrPoint(it.x, it.y) }
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

            val names = StageItemCatalogRepository.loadItemNames(context.assets, "chapter_5")
            val twoLinePatterns = TwoLineOcrPatterns.forStage("chapter_5")
            val matches = OcrGeometryMatcher.match(blocks, names, twoLinePatterns)
            val matchedNames = matches.map { it.itemName }.toSet()
            val diagnostic = blocks.mapIndexed { index, block ->
                val coordinates = block.corners.joinToString(" ") { "${it.x},${it.y}" }
                "#$index text=${block.text.replace("\n", " / ")} lines=${block.lines.joinToString(" / ")} corners=[$coordinates]"
            }.joinToString("\n")

            android.util.Log.i("Chapter5ReferenceOCR", "ML Kit blocks:\n$diagnostic")
            android.util.Log.i("Chapter5ReferenceOCR", "Matched labels: ${matches.map { it.itemName }}")

            assertTrue(
                "輸送書類 was not detected. Matched=$matchedNames\nML Kit blocks:\n$diagnostic",
                "輸送書類" in matchedNames
            )
            assertTrue(
                "バリケード was not detected. Matched=$matchedNames\nML Kit blocks:\n$diagnostic",
                "バリケード" in matchedNames
            )
        } finally {
            recognizer.close()
            bitmap.recycle()
        }
    }
}
