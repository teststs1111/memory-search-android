package jp.teststs1111.memorysearch

import java.text.Normalizer
import java.util.Locale

/**
 * Matches exact OCR labels. A two-line label may be joined only when both
 * lines belong to the same OCR text block; unrelated blocks are never joined.
 */
object OcrItemMatcher {
    fun normalize(value: String): String {
        return Normalizer.normalize(value, Normalizer.Form.NFKC)
            .lowercase(Locale.ROOT)
            .filterNot { it.isWhitespace() || Character.isSpaceChar(it) }
    }

    fun matchLines(ocrLines: List<String>, itemNames: List<String>): List<String> {
        return matchNormalizedCandidates(ocrLines, itemNames)
    }

    /**
     * Supports labels split across exactly two adjacent OCR lines.
     * Joining is deliberately limited to one pair per block to avoid
     * accidentally combining neighboring item labels.
     */
    fun matchBlocks(
        ocrBlocks: List<List<String>>,
        itemNames: List<String>,
        twoLinePatterns: List<TwoLineOcrPattern> = emptyList()
    ): List<String> {
        val candidates = ArrayList<String>()
        ocrBlocks.forEach { block ->
            block.forEach { line ->
                if (line.isNotBlank()) candidates.add(line)
            }
            block.zipWithNext().forEach { (first, second) ->
                if (twoLinePatterns.any { it.matches(first, second) }) {
                    candidates.add(first + second)
                }
            }
        }
        return matchNormalizedCandidates(candidates, itemNames)
    }

    private fun matchNormalizedCandidates(candidates: List<String>, itemNames: List<String>): List<String> {
        val normalized = candidates.map(::normalize).filter(String::isNotEmpty).toSet()
        if (normalized.isEmpty()) return emptyList()

        val matched = LinkedHashSet<String>()
        itemNames.forEach { itemName ->
            val name = normalize(itemName)
            if (name.isNotEmpty() && name in normalized) matched.add(itemName)
        }
        return matched.toList()
    }
}
