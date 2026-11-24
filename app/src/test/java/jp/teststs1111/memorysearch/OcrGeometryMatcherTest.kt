package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OcrGeometryMatcherTest {
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
            listOf("バリケード")
        )

        assertEquals("バリケード", result.single().itemName)
        assertEquals(corners, result.single().corners)
    }

    @Test
    fun doesNotJoinTextAcrossDifferentBlocks() {
        val result = OcrGeometryMatcher.match(
            listOf(
                OcrBlockGeometry("バリ", listOf("バリ"), listOf(OcrPoint(0, 0), OcrPoint(20, 0), OcrPoint(20, 10), OcrPoint(0, 10))),
                OcrBlockGeometry("ケード", listOf("ケード"), listOf(OcrPoint(30, 0), OcrPoint(70, 0), OcrPoint(70, 10), OcrPoint(30, 10)))
            ),
            listOf("バリケード")
        )
        assertTrue(result.isEmpty())
    }
}
