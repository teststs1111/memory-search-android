package jp.teststs1111.memorysearch

import android.content.res.AssetManager
import org.json.JSONObject

data class StageItemCatalog(
    val stageId: String,
    val stageName: String,
    val itemNames: List<String>,
    val reviewNotes: List<String> = emptyList()
)

object StageItemCatalogValidator {
    fun validate(catalogs: List<StageItemCatalog>) {
        val stageIds = HashSet<String>()
        catalogs.forEach { catalog ->
            require(catalog.stageId.matches(Regex("chapter_[0-9]+"))) {
                "Invalid stageId: ${catalog.stageId}"
            }
            require(stageIds.add(catalog.stageId)) {
                "Duplicate stageId: ${catalog.stageId}"
            }
            require(catalog.stageName.isNotBlank()) { "stageName must not be blank" }
            require(catalog.itemNames.isNotEmpty()) { "Catalog must contain item names: ${catalog.stageId}" }
            require(catalog.reviewNotes.all { it.isNotBlank() }) {
                "Review notes must not be blank: ${catalog.stageId}"
            }
            require(catalog.itemNames.all { it.isNotBlank() }) {
                "Item names must not be blank: ${catalog.stageId}"
            }
            require(catalog.itemNames.distinct().size == catalog.itemNames.size) {
                "Duplicate item name: ${catalog.stageId}"
            }
            val normalizedNames = catalog.itemNames.map(OcrItemMatcher::normalize)
            require(normalizedNames.all { it.isNotEmpty() }) {
                "Item names must not normalize to blank: ${catalog.stageId}"
            }
            require(normalizedNames.distinct().size == normalizedNames.size) {
                "Item names collide after OCR normalization: ${catalog.stageId}"
            }
        }
    }
}

object StageItemCatalogRepository {
    private const val CATALOG_FILE = "stages/item_catalogs.json"

    fun loadAll(assets: AssetManager): List<StageItemCatalog> {
        val jsonText = assets.open(CATALOG_FILE).bufferedReader().use { it.readText() }
        val root = JSONObject(jsonText)
        require(root.getInt("schemaVersion") == 1) { "Unsupported item catalog schema" }
        val chapters = root.getJSONArray("chapters")
        val catalogs = buildList {
            for (index in 0 until chapters.length()) {
                val chapter = chapters.getJSONObject(index)
                val namesJson = chapter.getJSONArray("itemNames")
                val names = buildList {
                    for (nameIndex in 0 until namesJson.length()) {
                        add(namesJson.getString(nameIndex))
                    }
                }
                val notesJson = chapter.optJSONArray("reviewNotes")
                val notes = buildList {
                    if (notesJson != null) {
                        for (noteIndex in 0 until notesJson.length()) {
                            add(notesJson.getString(noteIndex))
                        }
                    }
                }
                add(
                    StageItemCatalog(
                        stageId = chapter.getString("stageId"),
                        stageName = chapter.getString("stageName"),
                        itemNames = names,
                        reviewNotes = notes
                    )
                )
            }
        }
        StageItemCatalogValidator.validate(catalogs)
        return catalogs
    }

    fun loadItemNames(assets: AssetManager, stageId: String): List<String> {
        if (!stageId.matches(Regex("chapter_[0-9]+"))) return emptyList()
        return loadAll(assets).firstOrNull { it.stageId == stageId }?.itemNames.orEmpty()
    }

    fun loadReviewNotes(assets: AssetManager, stageId: String): List<String> {
        if (!stageId.matches(Regex("chapter_[0-9]+"))) return emptyList()
        return loadAll(assets).firstOrNull { it.stageId == stageId }?.reviewNotes.orEmpty()
    }
}
