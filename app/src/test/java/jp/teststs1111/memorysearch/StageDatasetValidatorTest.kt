package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class StageDatasetValidatorTest {
    private fun dataset(
        status: String = "verified",
        items: List<StageItem> = listOf(StageItem("item-1", "テストアイテム", 0.25, 0.75))
    ) = StageDataset(
        stageId = "chapter_1",
        stageName = "第1章",
        coordinateSystem = "normalized_0_to_1",
        referenceImage = "chapter_1_base.png",
        dataStatus = status,
        items = items
    )

    @Test
    fun acceptsNormalizedCoordinatesIncludingEdges() {
        StageDatasetValidator.validate(
            dataset(items = listOf(
                StageItem("left-top", "左上", 0.0, 0.0),
                StageItem("right-bottom", "右下", 1.0, 1.0)
            ))
        )
    }

    @Test
    fun rejectsCoordinatesOutsideNormalizedRange() {
        assertThrows(IllegalArgumentException::class.java) {
            StageDatasetValidator.validate(dataset(items = listOf(StageItem("bad", "不正", 1.01, 0.5))))
        }
    }

    @Test
    fun rejectsNonFiniteCoordinates() {
        assertThrows(IllegalArgumentException::class.java) {
            StageDatasetValidator.validate(dataset(items = listOf(StageItem("bad", "不正", Double.NaN, 0.5))))
        }
    }

    @Test
    fun rejectsDuplicateItemIds() {
        assertThrows(IllegalArgumentException::class.java) {
            StageDatasetValidator.validate(
                dataset(items = listOf(
                    StageItem("same", "品物A", 0.2, 0.3),
                    StageItem("same", "品物B", 0.7, 0.8)
                ))
            )
        }
    }

    @Test
    fun unverifiedDatasetCannotContainCoordinatesOrMarkers() {
        val unverified = dataset(status = "awaiting_coordinate_verification", items = emptyList())
        StageDatasetValidator.validate(unverified)
        assertEquals(emptyList<StageItem>(), StageDatasetValidator.markerItems(unverified))
    }

    @Test
    fun rejectsUnverifiedDatasetWithCoordinates() {
        assertThrows(IllegalArgumentException::class.java) {
            StageDatasetValidator.validate(dataset(status = "awaiting_coordinate_verification"))
        }
    }
}
