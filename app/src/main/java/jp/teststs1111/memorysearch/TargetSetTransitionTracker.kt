package jp.teststs1111.memorysearch

/**
 * Keeps the current three-item highlight set until a different complete trio
 * is observed consistently. Empty/partial OCR frames never clear active targets.
 *
 * This intentionally does not infer per-item completion from strike-through or
 * dimming. The whole set is replaced only after a stable next set is detected.
 */
class TargetSetTransitionTracker(
    private val requiredStableFrames: Int = 2
) {
    data class Update(
        val activeTargets: List<String>,
        val changed: Boolean
    )

    private var activeKey: List<String>? = null
    private var pendingKey: List<String>? = null
    private var pendingFrames = 0

    init {
        require(requiredStableFrames >= 1) { "requiredStableFrames must be positive" }
    }

    @Synchronized
    fun observe(recognizedNames: List<String>): Update {
        val candidate = recognizedNames
            .asSequence()
            .filter { it.isNotBlank() }
            .distinct()
            .sorted()
            .take(4)
            .toList()
            .takeIf { it.size == TARGET_COUNT }

        if (candidate == null || candidate == activeKey) {
            pendingKey = null
            pendingFrames = 0
            return Update(activeKey.orEmpty(), changed = false)
        }

        if (candidate == pendingKey) {
            pendingFrames += 1
        } else {
            pendingKey = candidate
            pendingFrames = 1
        }

        if (pendingFrames >= requiredStableFrames) {
            val changed = candidate != activeKey
            activeKey = candidate
            pendingKey = null
            pendingFrames = 0
            return Update(activeKey.orEmpty(), changed)
        }

        return Update(activeKey.orEmpty(), changed = false)
    }

    @Synchronized
    fun reset() {
        activeKey = null
        pendingKey = null
        pendingFrames = 0
    }

    companion object {
        const val TARGET_COUNT = 3
    }
}
