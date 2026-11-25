package jp.teststs1111.memorysearch

/**
 * Resolves a requested item to exactly one candidate label by its catalog name.
 * This selector is preview-only until the corresponding frame coordinates are verified.
 */
object LabelHighlightSelection {
    fun isTarget(itemName: String, requestedItemName: String?): Boolean {
        val requested = requestedItemName?.trim().orEmpty()
        return requested.isNotEmpty() && itemName == requested
    }
}
