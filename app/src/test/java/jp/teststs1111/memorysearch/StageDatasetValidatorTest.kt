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
    fun stageFileDiscoveryExcludesCatalogAndCandidateJsonFiles() {
        assertEquals(
            listOf("chapter_1.json", "chapter_2.json", "chapter_10.json"),
            StageDatasetRepository.stageDataFileNames(
                listOf(
                    "item_catalogs.json",
                    "chapter_10.json",
                    "chapter_1_label_boxes.candidates.json",
                    "chapter_2.json",
                    "chapter_1.json",
                    "notes.JSON"
                )
            )
        )
    }

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
    fun rejectsInvalidHighlightBoxDimensions() {
        assertThrows(IllegalArgumentException::class.java) {
            StageDatasetValidator.validate(dataset(items = listOf(StageItem("bad-width", "幅不正", 0.5, 0.5, 0.0, 0.1))))
        }
        assertThrows(IllegalArgumentException::class.java) {
            StageDatasetValidator.validate(dataset(items = listOf(StageItem("bad-height", "高さ不正", 0.5, 0.5, 0.1, 1.1))))
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
    fun itemLookupIsRestrictedToTheSelectedStage() {
        val chapterOne = dataset(
            items = listOf(StageItem("chapter-one-item", "赤いカップ", 0.2, 0.3))
        )
        val chapterTwo = dataset(
            items = listOf(StageItem("chapter-two-item", "赤いカップ", 0.8, 0.7))
        )

        assertEquals("chapter-one-item", StageDatasetValidator.findItem(chapterOne, "赤いカップ")?.itemId)
        assertEquals("chapter-two-item", StageDatasetValidator.findItem(chapterTwo, "赤いカップ")?.itemId)
    }

    @Test
    fun itemLookupTrimsWhitespaceButDoesNotGuessNames() {
        val verified = dataset()
        assertEquals("item-1", StageDatasetValidator.findItem(verified, "  テストアイテム  ")?.itemId)
        assertEquals(null, StageDatasetValidator.findItem(verified, "テストアイテム?"))
        assertEquals(null, StageDatasetValidator.findItem(verified, " "))
    }

    @Test
    fun unverifiedItemsAreNeverReturnedByLookup() {
        val unverified = dataset(status = "awaiting_coordinate_verification", items = emptyList())
        assertEquals(null, StageDatasetValidator.findItem(unverified, "テストアイテム"))
    }

    @Test
    fun rejectsUnverifiedDatasetWithCoordinates() {
        assertThrows(IllegalArgumentException::class.java) {
            StageDatasetValidator.validate(dataset(status = "awaiting_coordinate_verification"))
        }
    }
}
