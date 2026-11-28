package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OcrGeometryMatcherTest {
    private fun block(text: String, left: Int, top: Int, right: Int, bottom: Int) =
        OcrBlockGeometry(
            text,
            listOf(text),
            listOf(OcrPoint(left, top), OcrPoint(right, top), OcrPoint(right, bottom), OcrPoint(left, bottom))
        )

    @Test
    fun keepsRotatedFourCornersForExactTextMatch() {
        val corners = listOf(
            OcrPoint(120, 80),
            OcrPoint(260, 105),
            OcrPoint(250, 155),
            OcrPoint(110, 130)
        )
        val result = OcrGeometryMatcher.match(
            listOf(OcrBlockGeometry("信号紅炎", listOf("信号紅炎"), corners)),
            listOf("信号紅炎", "救急箱")
        )

        assertEquals(1, result.size)
        assertEquals("信号紅炎", result.single().itemName)
        assertEquals(corners, result.single().corners)
    }

    @Test
    fun joinsAdjacentLinesOnlyInsideOneTextBlockAndKeepsItsGeometry() {
        val corners = listOf(OcrPoint(10, 20), OcrPoint(90, 25), OcrPoint(88, 80), OcrPoint(8, 75))
        val result = OcrGeometryMatcher.match(
            listOf(OcrBlockGeometry("バリ\nケード", listOf("バリ", "ケード"), corners)),
            listOf("バリケード"),
            listOf(TwoLineOcrPattern("バリケード", "バリ", "ケード"))
        )

        assertEquals("バリケード", result.single().itemName)
        assertEquals(corners, result.single().corners)
    }

    @Test
    fun joinsTwoVerticallyStackedBlocksForBothKnownTwoLineLabels() {
        val result = OcrGeometryMatcher.match(
            listOf(
                block("バリ", 350, 350, 405, 370),
                block("ケード", 352, 373, 408, 393),
                block("輸送", 80, 675, 132, 695),
                block("書類", 82, 698, 134, 718)
            ),
            listOf("バリケード", "輸送書類"),
            listOf(
                TwoLineOcrPattern("バリケード", "バリ", "ケード"),
                TwoLineOcrPattern("輸送書類", "輸送", "書類")
            )
        )

        assertEquals(listOf("バリケード", "輸送書類"), result.map { it.itemName })
        assertEquals(listOf("バリケード", "輸送書類"), result.map { it.recognizedText })
        assertEquals(2, result.size)
    }

    @Test
    fun doesNotJoinSideBySideBlocks() {
        val result = OcrGeometryMatcher.match(
            listOf(block("バリ", 0, 0, 20, 10), block("ケード", 30, 0, 70, 10)),
            listOf("バリケード"),
            listOf(TwoLineOcrPattern("バリケード", "バリ", "ケード"))
        )
        assertTrue(result.isEmpty())
    }

    @Test
    fun doesNotJoinDistantOrUnevenlySizedBlocks() {
        val distant = OcrGeometryMatcher.match(
            listOf(block("バリ", 0, 0, 20, 10), block("ケード", 0, 40, 40, 50)),
            listOf("バリケード"),
            listOf(TwoLineOcrPattern("バリケード", "バリ", "ケード"))
        )
        val uneven = OcrGeometryMatcher.match(
            listOf(block("バリ", 0, 0, 20, 5), block("ケード", 0, 8, 40, 30)),
            listOf("バリケード"),
            listOf(TwoLineOcrPattern("バリケード", "バリ", "ケード"))
        )
        assertTrue(distant.isEmpty())
        assertTrue(uneven.isEmpty())
    }

    @Test
    fun doesNotSkipAnInterveningTextBlock() {
        val result = OcrGeometryMatcher.match(
            listOf(
                block("バリ", 0, 0, 40, 10),
                block("別", 2, 12, 38, 22),
                block("ケード", 0, 24, 40, 34)
            ),
            listOf("バリケード"),
            listOf(TwoLineOcrPattern("バリケード", "バリ", "ケード"))
        )
        assertTrue(result.isEmpty())
    }
}
