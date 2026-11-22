package jp.teststs1111.memorysearch

/**
 * Coordinates are normalized to the game-content rectangle, not the full device screen.
 */
data class StageItem(
    val itemId: String,
    val itemName: String,
    val x: Double,
    val y: Double
)

data class StageDataset(
    val stageId: String,
    val stageName: String,
    val coordinateSystem: String,
    val referenceImage: String,
    val dataStatus: String,
    val items: List<StageItem>
)

object StageDatasetValidator {
    private const val NORMALIZED_COORDINATES = "normalized_0_to_1"

    fun validate(dataset: StageDataset) {
        require(dataset.stageId.isNotBlank()) { "stageId must not be blank" }
        require(dataset.stageName.isNotBlank()) { "stageName must not be blank" }
        require(dataset.coordinateSystem == NORMALIZED_COORDINATES) {
            "Unsupported coordinateSystem: ${dataset.coordinateSystem}"
        }
        require(dataset.referenceImage.isNotBlank()) { "referenceImage must not be blank" }
        require(dataset.dataStatus == "awaiting_coordinate_verification" || dataset.dataStatus == "verified") {
            "Unsupported dataStatus: ${dataset.dataStatus}"
        }
        require(dataset.dataStatus == "verified" || dataset.items.isEmpty()) {
            "Unverified datasets must not contain marker coordinates"
        }

        val ids = HashSet<String>()
        dataset.items.forEach { item ->
            require(item.itemId.isNotBlank()) { "itemId must not be blank" }
            require(item.itemName.isNotBlank()) { "itemName must not be blank" }
            require(ids.add(item.itemId)) { "Duplicate itemId: ${item.itemId}" }
            require(item.x.isFinite() && item.x in 0.0..1.0) {
                "x must be a finite normalized coordinate for ${item.itemId}"
            }
            require(item.y.isFinite() && item.y in 0.0..1.0) {
                "y must be a finite normalized coordinate for ${item.itemId}"
            }
        }
    }

    /** Only verified coordinates may ever be used for marker placement. */
    fun markerItems(dataset: StageDataset): List<StageItem> =
        if (dataset.dataStatus == "verified") dataset.items else emptyList()

    /**
     * Search only within the explicitly selected stage. Unverified datasets
     * intentionally return no result, preventing accidental marker placement.
     */
    fun findItem(dataset: StageDataset, requestedName: String): StageItem? {
        val normalizedName = requestedName.trim()
        if (normalizedName.isEmpty()) return null
        return markerItems(dataset).firstOrNull { it.itemName == normalizedName }
    }
}
