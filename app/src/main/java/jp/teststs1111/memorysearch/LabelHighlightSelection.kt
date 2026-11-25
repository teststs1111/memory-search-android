package jp.teststs1111.memorysearch

/** Selects up to three exact catalog matches recognized on the game screen. */
object LabelHighlightSelection {
    const val MAX_VISIBLE_GAME_ITEMS = 3

    fun targets(itemNames: List<String>, requestedItemNames: Collection<String>): Set<String> {
        val requested = requestedItemNames.map(String::trim).filter(String::isNotEmpty).toSet()
        if (requested.isEmpty()) return emptySet()
        return itemNames.asSequence().filter { it in requested }.distinct()
            .take(MAX_VISIBLE_GAME_ITEMS).toCollection(LinkedHashSet())
    }

    fun isTarget(itemName: String, requestedItemNames: Set<String>): Boolean =
        itemName in requestedItemNames
}
