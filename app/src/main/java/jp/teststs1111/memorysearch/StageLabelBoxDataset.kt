package jp.teststs1111.memorysearch

import android.content.res.AssetManager
import org.json.JSONObject

data class NormalizedBounds(
    val left: Double,
    val top: Double,
    val right: Double,
    val bottom: Double
)

data class StageLabelBox(
    val itemId: String,
    val itemName: String,
    val bounds: NormalizedBounds,
    val source: String
)

data class StageLabelBoxDataset(
    val stageId: String,
    val coordinateSystem: String,
    val runtimeEnabled: Boolean,
    val dataStatus: String,
    val items: List<StageLabelBox>
)

object StageLabelBoxValidator {
    private const val NORMALIZED = "normalized_0_to_1"
    private const val REVIEWED_CANDIDATE = "candidate_reviewed_by_user_pending_final_check"
    private const val DRAFT_CANDIDATE = "candidate_draft_from_annotated_reference"

    fun validate(dataset: StageLabelBoxDataset) {
        require(dataset.stageId.isNotBlank()) { "stageId must not be blank" }
        require(dataset.coordinateSystem == NORMALIZED) {
            "Unsupported coordinateSystem: ${dataset.coordinateSystem}"
        }
        require(
            dataset.dataStatus == REVIEWED_CANDIDATE ||
                dataset.dataStatus == DRAFT_CANDIDATE ||
                dataset.dataStatus == "verified"
        ) {
            "Unsupported dataStatus: ${dataset.dataStatus}"
        }
        require(!dataset.runtimeEnabled || dataset.dataStatus == "verified") {
            "Label boxes cannot be enabled before final verification"
        }

        val ids = HashSet<String>()
        val names = HashSet<String>()
        dataset.items.forEach { item ->
            require(item.itemId.isNotBlank()) { "itemId must not be blank" }
            require(item.itemName.isNotBlank()) { "itemName must not be blank" }
            require(ids.add(item.itemId)) { "Duplicate itemId: ${item.itemId}" }
            require(names.add(item.itemName)) { "Duplicate itemName: ${item.itemName}" }
            val b = item.bounds
            require(
                listOf(b.left, b.top, b.right, b.bottom).all { it.isFinite() && it in 0.0..1.0 }
            ) { "Bounds must be finite normalized coordinates for ${item.itemId}" }
            require(b.left < b.right && b.top < b.bottom) {
                "Bounds must have positive width and height for ${item.itemId}"
            }
            require(item.source == "left" || item.source == "right" || item.source == "annotated") {
                "Unsupported source image for ${item.itemId}"
            }
        }
    }

    /** Candidate rectangles remain inert until explicitly verified and enabled. */
    fun activeBoxes(dataset: StageLabelBoxDataset): List<StageLabelBox> =
        if (dataset.runtimeEnabled && dataset.dataStatus == "verified") dataset.items else emptyList()

    fun findActiveBox(dataset: StageLabelBoxDataset, requestedName: String): StageLabelBox? {
        val name = requestedName.trim()
        if (name.isEmpty()) return null
        return activeBoxes(dataset).firstOrNull { it.itemName == name }
    }
}

object StageLabelBoxRepository {
    private const val CANDIDATE_FILE = "stages/chapter_1_label_boxes.candidates.json"

    fun loadChapterOneCandidates(assets: AssetManager): StageLabelBoxDataset =
        loadCandidatesForStage(assets, "chapter_1")

    fun loadCandidatesForStage(assets: AssetManager, stageId: String): StageLabelBoxDataset {
        require(stageId.matches(Regex("chapter_[0-9]+"))) { "Invalid stage ID: $stageId" }
        return loadCandidates(assets, stageId)
    }

    /**
     * Names may be used for OCR matching while candidate rectangles remain inactive.
     * A missing chapter file produces an empty catalog rather than borrowing another chapter.
     */
    fun loadCandidateItemNames(assets: AssetManager, stageId: String): List<String> {
        if (!stageId.matches(Regex("chapter_[0-9]+"))) return emptyList()
        val fileName = "${stageId}_label_boxes.candidates.json"
        if (assets.list("stages")?.contains(fileName) != true) return emptyList()
        val dataset = loadCandidates(assets, stageId)
        return dataset.items.map { it.itemName }
    }

    private fun loadCandidates(assets: AssetManager, stageId: String): StageLabelBoxDataset {
        val fileName = "stages/${stageId}_label_boxes.candidates.json"
        val jsonText = assets.open(fileName).bufferedReader().use { it.readText() }
        return parse(jsonText).also { dataset ->
            require(dataset.stageId == stageId) { "Stage ID mismatch in $fileName" }
        }
    }

    internal fun parse(jsonText: String): StageLabelBoxDataset {
        val json = JSONObject(jsonText)
        val itemsJson = json.getJSONArray("items")
        val items = buildList {
            for (index in 0 until itemsJson.length()) {
                val item = itemsJson.getJSONObject(index)
                val bounds = item.getJSONObject("bounds")
                add(
                    StageLabelBox(
                        itemId = item.getString("itemId"),
                        itemName = item.getString("itemName"),
                        bounds = NormalizedBounds(
                            left = bounds.getDouble("left"),
                            top = bounds.getDouble("top"),
                            right = bounds.getDouble("right"),
                            bottom = bounds.getDouble("bottom")
                        ),
                        source = item.getString("source")
                    )
                )
            }
        }
        return StageLabelBoxDataset(
            stageId = json.getString("stageId"),
            coordinateSystem = json.getString("coordinateSystem"),
            runtimeEnabled = json.getBoolean("runtimeEnabled"),
            dataStatus = json.getString("dataStatus"),
            items = items
        ).also(StageLabelBoxValidator::validate)
    }
}
