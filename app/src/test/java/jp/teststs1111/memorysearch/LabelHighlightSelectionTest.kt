package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LabelHighlightSelectionTest {
    @Test
    fun selectsUpToThreeExactRecognizedItemsInCatalogOrder() {
        val catalog = listOf("バリケード", "輸送書類", "工具箱", "救急箱")
        assertEquals(
            linkedSetOf("バリケード", "輸送書類", "工具箱"),
            LabelHighlightSelection.targets(catalog, listOf("輸送書類", "工具箱", "バリケード", "未知"))
        )
    }

    @Test
    fun neverSelectsMoreThanThreeItems() {
        val catalog = listOf("A", "B", "C", "D")
        assertEquals(linkedSetOf("A", "B", "C"), LabelHighlightSelection.targets(catalog, catalog))
    }

    @Test
    fun ignoresBlankUnknownAndPartialMatches() {
        assertTrue(LabelHighlightSelection.targets(
            listOf("バリケード", "輸送書類"),
            listOf("", "輸送", "存在しない")
        ).isEmpty())
    }

    @Test
    fun onlySelectedNamesGlow() {
        val targets = setOf("バリケード", "輸送書類", "工具箱")
        assertTrue(LabelHighlightSelection.isTarget("バリケード", targets))
        assertTrue(LabelHighlightSelection.isTarget("輸送書類", targets))
        assertFalse(LabelHighlightSelection.isTarget("救急箱", targets))
    }
}
