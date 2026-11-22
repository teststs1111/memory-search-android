package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Test

class OcrItemMatcherTest {
    @Test
    fun matchesExactJapaneseLine() {
        assertEquals(listOf("テディベア"), OcrItemMatcher.matchLines(listOf("テディベア"), listOf("マグカップ", "テディベア")))
    }

    @Test
    fun normalizesFullWidthAndWhitespace() {
        assertEquals(listOf("ＡＢＣ１２３"), OcrItemMatcher.matchLines(listOf(" ABC 123 "), listOf("ＡＢＣ１２３")))
    }

    @Test
    fun doesNotMatchSubstringOfAnotherItemName() {
        assertEquals(listOf("コーヒー牛乳"), OcrItemMatcher.matchLines(listOf("コーヒー牛乳"), listOf("牛乳", "コーヒー牛乳")))
    }

    @Test
    fun ignoresBlankLinesAndUnknownText() {
        assertEquals(emptyList<String>(), OcrItemMatcher.matchLines(listOf("", "　", "読み取れない文字"), listOf("テディベア")))
    }

    @Test
    fun matchesOnlyAgainstTheCurrentlySelectedChapterCatalog() {
        val recognizedLines = listOf("テディベア")
        assertEquals(listOf("テディベア"), OcrItemMatcher.matchLines(recognizedLines, listOf("マグカップ", "テディベア")))
        assertEquals(emptyList<String>(), OcrItemMatcher.matchLines(recognizedLines, listOf("赤い本", "青い箱")))
    }

    @Test
    fun returnsEachMatchedItemOnlyOnceInCatalogOrder() {
        assertEquals(
            listOf("マグカップ", "テディベア"),
            OcrItemMatcher.matchLines(listOf("テディベア", "マグカップ", "テディベア"), listOf("マグカップ", "テディベア"))
        )
    }

    @Test
    fun matchesTwoAdjacentLinesInsideOneBlock() {
        assertEquals(
            listOf("星型チャーム"),
            OcrItemMatcher.matchBlocks(listOf(listOf("星型", "チャーム")), listOf("星型チャーム"))
        )
    }

    @Test
    fun doesNotJoinLinesAcrossDifferentBlocks() {
        assertEquals(
            emptyList<String>(),
            OcrItemMatcher.matchBlocks(listOf(listOf("星型"), listOf("チャーム")), listOf("星型チャーム"))
        )
    }

    @Test
    fun doesNotJoinThreeLinesOrUseSubstringMatches() {
        assertEquals(
            emptyList<String>(),
            OcrItemMatcher.matchBlocks(listOf(listOf("星", "型", "チャーム")), listOf("星型チャーム", "チャーム"))
        )
    }

    @Test
    fun preservesExactLineMatchesAlongsideSplitMatches() {
        assertEquals(
            listOf("星型チャーム", "テディベア"),
            OcrItemMatcher.matchBlocks(
                listOf(listOf("星型", "チャーム"), listOf("テディベア")),
                listOf("星型チャーム", "テディベア")
            )
        )
    }
}
