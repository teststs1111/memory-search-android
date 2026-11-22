package jp.teststs1111.memorysearch

import java.text.Normalizer
import java.util.Locale

/**
 * Matches OCR line text to item names without fuzzy substring matches.
 *
 * Exact line matching is intentional: substring matching would incorrectly
 * match "牛乳" inside "コーヒー牛乳" and could light up the wrong label.
 */
object OcrItemMatcher {
    fun normalize(value: String): String {
        return Normalizer.normalize(value, Normalizer.Form.NFKC)
            .lowercase(Locale.ROOT)
            .filterNot { it.isWhitespace() || it.isSpaceChar() }
    }

    fun matchLines(ocrLines: List<String>, itemNames: List<String>): List<String> {
        val normalizedLines = ocrLines.map(::normalize).filter(String::isNotEmpty).toSet()
        if (normalizedLines.isEmpty()) return emptyList()

        val matched = LinkedHashSet<String>()
        itemNames.forEach { itemName ->
            val normalizedName = normalize(itemName)
            if (normalizedName.isNotEmpty() && normalizedName in normalizedLines) {
                matched.add(itemName)
            }
        }
        return matched.toList()
    }
}
