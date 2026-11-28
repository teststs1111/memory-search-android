package jp.teststs1111.memorysearch

/**
 * The game's three target buttons occupy the same bottom strip on every stage.
 * Coordinates are normalized so the region scales with the captured display size.
 */
object TargetStripRegion {
    private const val LEFT = 0.035
    private const val RIGHT = 0.965
    private const val TOP = 0.82
    private const val BOTTOM = 0.925

    fun contains(block: OcrBlockGeometry, imageWidth: Int, imageHeight: Int): Boolean {
        if (imageWidth <= 0 || imageHeight <= 0 || block.corners.size != 4) return false

        val centerX = block.corners.map { it.x }.average() / imageWidth
        val centerY = block.corners.map { it.y }.average() / imageHeight
        return centerX in LEFT..RIGHT && centerY in TOP..BOTTOM
    }

    fun filter(
        blocks: List<OcrBlockGeometry>,
        imageWidth: Int,
        imageHeight: Int
    ): List<OcrBlockGeometry> = blocks.filter { contains(it, imageWidth, imageHeight) }
}
