package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Test

class OcrItemMatcherTest {
    @Test
    fun matchesExactJapaneseLine() {
        assertEquals(
            listOf("テディベア"),
            OcrItemMatcher.matchLines(listOf("テディベア"), listOf("マグカップ", "テディベア"))
        )
    }

    @Test
    fun normalizesFullWidthAndWhitespace() {
        assertEquals(
            listOf("ＡＢＣ１２３"),
            OcrItemMatcher.matchLines(listOf(" ABC 123 "), listOf("ＡＢＣ１２３"))
        )
    }

    @Test
    fun doesNotMatchSubstringOfAnotherItemName() {
        assertEquals(
            listOf("コーヒー牛乳"),
            OcrItemMatcher.matchLines(listOf("コーヒー牛乳"), listOf("牛乳", "コーヒー牛乳"))
        )
    }

    @Test
    fun ignoresBlankLinesAndUnknownText() {
        assertEquals(
            emptyList<String>(),
            OcrItemMatcher.matchLines(listOf("", "　", "読み取れない文字"), listOf("テディベア"))
        )
    }

    @Test
    fun returnsEachMatchedItemOnlyOnceInCatalogOrder() {
        assertEquals(
            listOf("マグカップ", "テディベア"),
            OcrItemMatcher.matchLines(
                listOf("テディベア", "マグカップ", "テディベア"),
                listOf("マグカップ", "テディベア")
            )
        )
    }
}
