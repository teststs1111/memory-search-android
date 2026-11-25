package jp.teststs1111.memorysearch

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LabelHighlightSelectionTest {
    @Test
    fun highlightsOnlyTheExactlyRequestedItem() {
        assertTrue(LabelHighlightSelection.isTarget("バリケード", "バリケード"))
        assertFalse(LabelHighlightSelection.isTarget("輸送書類", "バリケード"))
    }

    @Test
    fun ignoresBlankOrMissingRequests() {
        assertFalse(LabelHighlightSelection.isTarget("バリケード", null))
        assertFalse(LabelHighlightSelection.isTarget("バリケード", "  "))
    }

    @Test
    fun trimsRequestButDoesNotUsePartialOrFuzzyMatching() {
        assertTrue(LabelHighlightSelection.isTarget("輸送書類", " 輸送書類 "))
        assertFalse(LabelHighlightSelection.isTarget("輸送書類", "輸送"))
        assertFalse(LabelHighlightSelection.isTarget("バリケード", "バリ ケード"))
    }
}
