package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

class StageLabelBoxValidatorTest {
    private fun dataset(
        enabled: Boolean = false,
        status: String = "candidate_reviewed_by_user_pending_final_check",
        items: List<StageLabelBox> = listOf(
            StageLabelBox("item-1", "テディベア", NormalizedBounds(0.2, 0.3, 0.4, 0.5), "left")
        )
    ) = StageLabelBoxDataset(
        stageId = "chapter_1",
        coordinateSystem = "normalized_0_to_1",
        runtimeEnabled = enabled,
        dataStatus = status,
        items = items
    )

    @Test
    fun acceptsCandidateBoundsButKeepsThemInactive() {
        val candidate = dataset()
        StageLabelBoxValidator.validate(candidate)
        assertEquals(emptyList<StageLabelBox>(), StageLabelBoxValidator.activeBoxes(candidate))
        assertNull(StageLabelBoxValidator.findActiveBox(candidate, "テディベア"))
    }

    @Test
    fun rejectsEnablingCandidateBeforeVerification() {
        assertThrows(IllegalArgumentException::class.java) {
            StageLabelBoxValidator.validate(dataset(enabled = true))
        }
    }

    @Test
    fun verifiedAndEnabledDatasetCanResolveExactName() {
        val enabled = dataset(enabled = true, status = "verified")
        assertEquals("item-1", StageLabelBoxValidator.findActiveBox(enabled, " テディベア ")?.itemId)
        assertNull(StageLabelBoxValidator.findActiveBox(enabled, "テディベア?"))
    }

    @Test
    fun rejectsInvalidOrInvertedBounds() {
        assertThrows(IllegalArgumentException::class.java) {
            StageLabelBoxValidator.validate(
                dataset(items = listOf(
                    StageLabelBox("bad", "不正", NormalizedBounds(0.8, 0.2, 0.3, 0.7), "left")
                ))
            )
        }
    }

    @Test
    fun rejectsDuplicateNames() {
        assertThrows(IllegalArgumentException::class.java) {
            StageLabelBoxValidator.validate(
                dataset(items = listOf(
                    StageLabelBox("first", "同じ名前", NormalizedBounds(0.1, 0.1, 0.2, 0.2), "left"),
                    StageLabelBox("second", "同じ名前", NormalizedBounds(0.3, 0.3, 0.4, 0.4), "right")
                ))
            )
        }
    }

    @Test
    fun acceptsDraftFromSingleAnnotatedReferenceButKeepsItInactive() {
        val draft = StageLabelBoxDataset(
            stageId = "chapter_5",
            coordinateSystem = "normalized_0_to_1",
            runtimeEnabled = false,
            dataStatus = "candidate_draft_from_annotated_reference",
            items = listOf(
                StageLabelBox(
                    "chapter_5_item_01",
                    "コードリール",
                    NormalizedBounds(0.1, 0.1, 0.3, 0.2),
                    "annotated"
                )
            )
        )
        StageLabelBoxValidator.validate(draft)
        assertEquals(emptyList<StageLabelBox>(), StageLabelBoxValidator.activeBoxes(draft))
    }

    @Test
    fun rejectsEnablingDraftAnnotatedCandidates() {
        val draft = dataset(enabled = true, status = "candidate_draft_from_annotated_reference")
        assertThrows(IllegalArgumentException::class.java) {
            StageLabelBoxValidator.validate(draft)
        }
    }

    @Test
    fun rejectsDuplicateIds() {
        assertThrows(IllegalArgumentException::class.java) {
            StageLabelBoxValidator.validate(
                dataset(items = listOf(
                    StageLabelBox("same", "品物A", NormalizedBounds(0.1, 0.1, 0.2, 0.2), "left"),
                    StageLabelBox("same", "品物B", NormalizedBounds(0.3, 0.3, 0.4, 0.4), "right")
                ))
            )
        }
    }
}
