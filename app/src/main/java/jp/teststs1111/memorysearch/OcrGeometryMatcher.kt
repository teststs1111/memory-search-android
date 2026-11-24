package jp.teststs1111.memorysearch

data class OcrPoint(val x: Int, val y: Int)

data class OcrBlockGeometry(
    val text: String,
    val lines: List<String>,
    val corners: List<OcrPoint>
)

data class OcrLocatedItem(
    val itemName: String,
    val recognizedText: String,
    val corners: List<OcrPoint>
)

/**
 * Keeps ML Kit's detected text quadrilateral attached to an exact catalog match.
 * Coordinates remain in the source image's pixel space; no guessed offset is added.
 */
object OcrGeometryMatcher {
    fun match(blocks: List<OcrBlockGeometry>, itemNames: List<String>): List<OcrLocatedItem> {
        val byNormalizedText = LinkedHashMap<String, OcrBlockGeometry>()
        blocks.forEach { block ->
            if (block.corners.size != 4) return@forEach
            val candidates = ArrayList<String>()
            candidates.add(block.text)
            candidates.addAll(block.lines)
            block.lines.zipWithNext().forEach { (first, second) ->
                candidates.add(first + second)
            }
            candidates.map(OcrItemMatcher::normalize)
                .filter(String::isNotEmpty)
                .forEach { normalized -> byNormalizedText.putIfAbsent(normalized, block) }
        }

        val result = ArrayList<OcrLocatedItem>()
        itemNames.forEach { itemName ->
            val normalizedName = OcrItemMatcher.normalize(itemName)
            val block = byNormalizedText[normalizedName] ?: return@forEach
            result.add(OcrLocatedItem(itemName, block.text, block.corners))
        }
        return result
    }
}
