package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TargetSetTransitionTrackerTest {
    @Test
    fun activatesInitialTrioOnlyAfterStableFrames() {
        val tracker = TargetSetTransitionTracker()
        assertTrue(tracker.observe(listOf("A", "B", "C")).activeTargets.isEmpty())
        val second = tracker.observe(listOf("C", "A", "B"))
        assertTrue(second.changed)
        assertEquals(listOf("A", "B", "C"), second.activeTargets)
    }

    @Test
    fun keepsOldHighlightsUntilDifferentTrioIsStable() {
        val tracker = TargetSetTransitionTracker()
        tracker.observe(listOf("A", "B", "C"))
        tracker.observe(listOf("A", "B", "C"))

        val partial = tracker.observe(listOf("A", "B"))
        assertFalse(partial.changed)
        assertEquals(listOf("A", "B", "C"), partial.activeTargets)

        val firstNewFrame = tracker.observe(listOf("D", "E", "F"))
        assertFalse(firstNewFrame.changed)
        assertEquals(listOf("A", "B", "C"), firstNewFrame.activeTargets)

        val secondNewFrame = tracker.observe(listOf("F", "D", "E"))
        assertTrue(secondNewFrame.changed)
        assertEquals(listOf("D", "E", "F"), secondNewFrame.activeTargets)
    }

    @Test
    fun ignoresDuplicateNamesAndRequiresExactlyThreeDistinctTargets() {
        val tracker = TargetSetTransitionTracker()
        assertTrue(tracker.observe(listOf("A", "A", "B")).activeTargets.isEmpty())
        assertTrue(tracker.observe(listOf("A", "A", "B")).activeTargets.isEmpty())
    }

    @Test
    fun transientDifferentTrioDoesNotReplaceCurrentSet() {
        val tracker = TargetSetTransitionTracker()
        tracker.observe(listOf("A", "B", "C"))
        tracker.observe(listOf("A", "B", "C"))

        tracker.observe(listOf("D", "E", "F"))
        val back = tracker.observe(listOf("A", "B", "C"))
        assertFalse(back.changed)
        assertEquals(listOf("A", "B", "C"), back.activeTargets)
    }

    @Test
    fun resetClearsActiveAndPendingSets() {
        val tracker = TargetSetTransitionTracker()
        tracker.observe(listOf("A", "B", "C"))
        tracker.observe(listOf("A", "B", "C"))
        tracker.reset()
        assertTrue(tracker.observe(listOf("D", "E", "F")).activeTargets.isEmpty())
    }
}
