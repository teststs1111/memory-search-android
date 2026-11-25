package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TargetStripRegionTest {
    private fun block(left: Int, top: Int, right: Int, bottom: Int) = OcrBlockGeometry(
        text = "target",
        lines = listOf("target"),
        corners = listOf(
            OcrPoint(left, top),
            OcrPoint(right, top),
            OcrPoint(right, bottom),
            OcrPoint(left, bottom)
        )
    )

    @Test
    fun includesTargetButtonsAtReferenceImageScale() {
        assertTrue(TargetStripRegion.contains(block(35, 620, 90, 640), 332, 720))
        assertTrue(TargetStripRegion.contains(block(130, 620, 190, 640), 332, 720))
        assertTrue(TargetStripRegion.contains(block(245, 620, 300, 640), 332, 720))
    }

    @Test
    fun scalesWithDifferentCaptureDimensions() {
        assertTrue(TargetStripRegion.contains(block(70, 1240, 180, 1280), 664, 1440))
    }

    @Test
    fun excludesBoardLabelsAndBottomControls() {
        assertFalse(TargetStripRegion.contains(block(100, 300, 150, 330), 332, 720))
        assertFalse(TargetStripRegion.contains(block(100, 680, 150, 700), 332, 720))
    }

    @Test
    fun rejectsMissingGeometryAndInvalidDimensions() {
        assertFalse(TargetStripRegion.contains(OcrBlockGeometry("x", listOf("x"), emptyList()), 332, 720))
        assertFalse(TargetStripRegion.contains(block(35, 620, 90, 640), 0, 720))
    }

    @Test
    fun filtersOnlyBlocksInsideTheCommonTargetStrip() {
        val inside = block(35, 620, 90, 640)
        val outside = block(100, 300, 150, 330)
        assertEquals(listOf(inside), TargetStripRegion.filter(listOf(outside, inside), 332, 720))
    }
}
