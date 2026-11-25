package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Test

class StageTargetResolverTest {
    private fun dataset(
        status: String = "verified",
        items: List<StageItem> = listOf(
            StageItem("a", "バリケード", 0.10, 0.20),
            StageItem("b", "輸送書類", 0.30, 0.40),
            StageItem("c", "懐中電灯", 0.50, 0.60),
            StageItem("d", "救急箱", 0.70, 0.80)
        )
    ) = StageDataset(
        stageId = "chapter_5",
        stageName = "第5章",
        coordinateSystem = "normalized_0_to_1",
        referenceImage = "reference/chapter_05/base.jpg",
        dataStatus = status,
        items = items
    )

    @Test
    fun resolvesExactNamesToSavedCoordinatesInTargetOrder() {
        val resolved = StageTargetResolver.resolve(
            dataset(),
            listOf("輸送書類", "バリケード", "存在しない項目")
        )

        assertEquals(listOf("b", "a"), resolved.map { it.itemId })
        assertEquals(listOf(0.30, 0.10), resolved.map { it.x })
    }

    @Test
    fun neverUsesCoordinatesFromUnverifiedDataset() {
        val unverified = dataset(
            status = "awaiting_coordinate_verification",
            items = emptyList()
        )

        assertEquals(emptyList<StageItem>(), StageTargetResolver.resolve(unverified, listOf("バリケード")))
    }

    @Test
    fun limitsResultsToThreeAndIgnoresDuplicateTargetNames() {
        val resolved = StageTargetResolver.resolve(
            dataset(),
            listOf("バリケード", "バリケード", "輸送書類", "懐中電灯", "救急箱")
        )

        assertEquals(listOf("a", "b", "c"), resolved.map { it.itemId })
    }

    @Test
    fun doesNotFuzzyMatchNamesOrInventMissingCoordinates() {
        val resolved = StageTargetResolver.resolve(
            dataset(),
            listOf("バリケード!", "輸送 書類", "懐中電灯")
        )

        assertEquals(listOf("c"), resolved.map { it.itemId })
    }

    @Test
    fun returnsNoTargetsForNonPositiveLimit() {
        assertEquals(emptyList<StageItem>(), StageTargetResolver.resolve(dataset(), listOf("バリケード"), 0))
    }
}
