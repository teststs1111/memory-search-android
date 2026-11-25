package jp.teststs1111.memorysearch

/** An explicitly approved two-row spelling in a reference image. */
data class TwoLineOcrPattern(
    val itemName: String,
    val firstLine: String,
    val secondLine: String
) {
    fun matches(first: String, second: String): Boolean =
        OcrItemMatcher.normalize(first) == OcrItemMatcher.normalize(firstLine) &&
            OcrItemMatcher.normalize(second) == OcrItemMatcher.normalize(secondLine)
}

/**
 * Per-chapter exceptions confirmed from the reference material.
 * Add entries only after the user confirms that a label is printed on two rows.
 */
object TwoLineOcrPatterns {
    private val byStage = mapOf(
        "chapter_5" to listOf(
            TwoLineOcrPattern("バリケード", "バリ", "ケード"),
            TwoLineOcrPattern("輸送書類", "輸送", "書類")
        )
    )

    fun forStage(stageId: String): List<TwoLineOcrPattern> = byStage[stageId].orEmpty()
}
