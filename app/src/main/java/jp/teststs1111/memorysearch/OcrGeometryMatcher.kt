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
 * Matches exact OCR text while retaining its source-image geometry.
 *
 * ML Kit can place the two visual rows of one label in separate text blocks.
 * Such blocks are joined only when their geometry strongly indicates a
 * vertically stacked pair; unrelated side-by-side or distant blocks stay
 * separate. The returned quadrilateral is the union of the two text bounds,
 * not an estimate of the outer label frame.
 */
object OcrGeometryMatcher {
    private data class Bounds(
        val left: Int,
        val top: Int,
        val right: Int,
        val bottom: Int
    ) {
        val width: Int get() = right - left
        val height: Int get() = bottom - top
        val centerX: Double get() = (left + right) / 2.0
        val centerY: Double get() = (top + bottom) / 2.0
    }

    fun match(blocks: List<OcrBlockGeometry>, itemNames: List<String>): List<OcrLocatedItem> {
        val byNormalizedText = LinkedHashMap<String, OcrLocatedItem>()

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
                .forEach { normalized ->
                    byNormalizedText.putIfAbsent(
                        normalized,
                        OcrLocatedItem(block.text, block.text, block.corners)
                    )
                }
        }

        // A pair may cross ML Kit block boundaries only when both blocks
        // contain one line and their quadrilaterals form a close vertical stack.
        for (firstIndex in blocks.indices) {
            val first = blocks[firstIndex]
            val firstLine = first.lines.singleOrNull { it.isNotBlank() } ?: continue
            val firstBounds = bounds(first.corners) ?: continue

            for (secondIndex in firstIndex + 1 until blocks.size) {
                val second = blocks[secondIndex]
                val secondLine = second.lines.singleOrNull { it.isNotBlank() } ?: continue
                val secondBounds = bounds(second.corners) ?: continue
                val pair = verticalPair(firstBounds, secondBounds) ?: continue
                if (hasInterveningBlock(blocks, firstIndex, secondIndex, pair.first, pair.second)) continue

                val recognized = pair.third.first + pair.third.second
                val normalized = OcrItemMatcher.normalize(recognized)
                if (normalized.isEmpty()) continue
                byNormalizedText.putIfAbsent(
                    normalized,
                    OcrLocatedItem(
                        itemName = "",
                        recognizedText = recognized,
                        corners = rectangleCorners(pair.first, pair.second)
                    )
                )
            }
        }

        val result = ArrayList<OcrLocatedItem>()
        itemNames.forEach { itemName ->
            val candidate = byNormalizedText[OcrItemMatcher.normalize(itemName)] ?: return@forEach
            result.add(candidate.copy(itemName = itemName))
        }
        return result
    }

    private fun bounds(corners: List<OcrPoint>): Bounds? {
        if (corners.size != 4) return null
        val left = corners.minOf { it.x }
        val top = corners.minOf { it.y }
        val right = corners.maxOf { it.x }
        val bottom = corners.maxOf { it.y }
        if (right <= left || bottom <= top) return null
        return Bounds(left, top, right, bottom)
    }

    private fun verticalPair(a: Bounds, b: Bounds): Triple<Bounds, Bounds, Pair<String, String>>? {
        val (upper, lower) = if (a.centerY <= b.centerY) a to b else b to a
        val minWidth = minOf(upper.width, lower.width).toDouble()
        val maxWidth = maxOf(upper.width, lower.width).toDouble()
        val minHeight = minOf(upper.height, lower.height).toDouble()
        val maxHeight = maxOf(upper.height, lower.height).toDouble()
        if (minWidth <= 0.0 || minHeight <= 0.0) return null

        val overlap = (minOf(upper.right, lower.right) - maxOf(upper.left, lower.left)).coerceAtLeast(0)
        val overlapRatio = overlap / minWidth
        val centerOffset = kotlin.math.abs(upper.centerX - lower.centerX)
        val verticalGap = lower.top - upper.bottom

        if (overlapRatio < 0.45) return null
        if (centerOffset > maxWidth * 0.45) return null
        if (verticalGap < -maxHeight * 0.25 || verticalGap > maxHeight * 1.0) return null
        if (maxHeight / minHeight > 2.0) return null
        return Triple(upper, lower, Pair("", ""))
    }

    private fun hasInterveningBlock(
        blocks: List<OcrBlockGeometry>,
        firstIndex: Int,
        secondIndex: Int,
        upper: Bounds,
        lower: Bounds
    ): Boolean {
        return blocks.indices.any { index ->
            if (index == firstIndex || index == secondIndex) return@any false
            val middle = bounds(blocks[index].corners) ?: return@any false
            middle.centerY > upper.centerY &&
                middle.centerY < lower.centerY &&
                (minOf(upper.right, middle.right) - maxOf(upper.left, middle.left)).coerceAtLeast(0) >=
                    minOf(upper.width, middle.width) * 0.3
        }
    }

    private fun rectangleCorners(upper: Bounds, lower: Bounds): List<OcrPoint> {
        val left = minOf(upper.left, lower.left)
        val top = minOf(upper.top, lower.top)
        val right = maxOf(upper.right, lower.right)
        val bottom = maxOf(upper.bottom, lower.bottom)
        return listOf(
            OcrPoint(left, top),
            OcrPoint(right, top),
            OcrPoint(right, bottom),
            OcrPoint(left, bottom)
        )
    }
}
