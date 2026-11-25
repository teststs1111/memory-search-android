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
    fun matchesOnlyAnExplicitlyRegisteredTwoLinePatternInsideOneBlock() {
        assertEquals(
            listOf("バリケード"),
            OcrItemMatcher.matchBlocks(
                listOf(listOf("バリ", "ケード")),
                listOf("バリケード"),
                listOf(TwoLineOcrPattern("バリケード", "バリ", "ケード"))
            )
        )
    }

    @Test
    fun doesNotJoinAnUnregisteredTwoLineLabel() {
        assertEquals(
            emptyList<String>(),
            OcrItemMatcher.matchBlocks(
                listOf(listOf("星型", "チャーム")),
                listOf("星型チャーム"),
                listOf(TwoLineOcrPattern("バリケード", "バリ", "ケード"))
            )
        )
    }

    @Test
    fun doesNotJoinLinesAcrossDifferentBlocksWithoutGeometryMatcher() {
        assertEquals(
            emptyList<String>(),
            OcrItemMatcher.matchBlocks(listOf(listOf("バリ"), listOf("ケード")), listOf("バリケード"))
        )
    }

    @Test
    fun doesNotJoinThreeLinesOrUseSubstringMatches() {
        assertEquals(
            emptyList<String>(),
            OcrItemMatcher.matchBlocks(listOf(listOf("星", "型", "チャーム")), listOf("星型チャーム"))
        )
    }

    @Test
    fun preservesExactLineMatchesAlongsideSplitMatches() {
        assertEquals(
            listOf("バリケード", "テディベア"),
            OcrItemMatcher.matchBlocks(
                listOf(listOf("バリ", "ケード"), listOf("テディベア")),
                listOf("バリケード", "テディベア"),
                listOf(TwoLineOcrPattern("バリケード", "バリ", "ケード"))
            )
        )
    }
}
