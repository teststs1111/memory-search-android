package jp.teststs1111.memorysearch

/**
 * Resolves the currently recognized target names to the selected stage's saved
 * coordinates. This deliberately never uses OCR text geometry as marker geometry.
 */
object StageTargetResolver {
    fun resolve(
        dataset: StageDataset,
        activeTargetNames: Collection<String>,
        maxTargets: Int = MAX_TARGETS
    ): List<StageItem> {
        if (maxTargets <= 0) return emptyList()

        val verifiedItems = StageDatasetValidator.markerItems(dataset)
        if (verifiedItems.isEmpty()) return emptyList()

        val byExactName = verifiedItems.associateBy(StageItem::itemName)
        val seen = HashSet<String>()
        return activeTargetNames.asSequence()
            .map(String::trim)
            .filter { it.isNotEmpty() && seen.add(it) }
            .mapNotNull(byExactName::get)
            .take(maxTargets)
            .toList()
    }

    const val MAX_TARGETS = 3
}
