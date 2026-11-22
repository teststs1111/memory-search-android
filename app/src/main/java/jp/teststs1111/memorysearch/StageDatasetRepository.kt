package jp.teststs1111.memorysearch

import android.content.res.AssetManager
import org.json.JSONObject

object StageDatasetRepository {
    private val stageFilePattern = Regex("^chapter_[0-9]+\\.json$", RegexOption.IGNORE_CASE)

    internal fun stageDataFileNames(fileNames: List<String>): List<String> {
        return fileNames
            .filter { stageFilePattern.matches(it) }
            .sortedBy { it.substringAfter('_').substringBefore('.').toIntOrNull() ?: Int.MAX_VALUE }
    }

    fun loadStages(assets: AssetManager): List<StageDataset> {
        val files = stageDataFileNames(assets.list("stages")?.toList().orEmpty())

        return files.map { fileName ->
            val json = assets.open("stages/$fileName").bufferedReader().use { it.readText() }
            parse(json)
        }.sortedBy { dataset ->
            dataset.stageId.substringAfterLast('_').toIntOrNull() ?: Int.MAX_VALUE
        }
    }

    internal fun parse(jsonText: String): StageDataset {
        val json = JSONObject(jsonText)
        val itemsJson = json.optJSONArray("items")
        val items = buildList {
            if (itemsJson != null) {
                for (index in 0 until itemsJson.length()) {
                    val item = itemsJson.getJSONObject(index)
                    add(
                        StageItem(
                            itemId = item.getString("itemId"),
                            itemName = item.getString("itemName"),
                            x = item.getDouble("x"),
                            y = item.getDouble("y")
                        )
                    )
                }
            }
        }

        val dataset = StageDataset(
            stageId = json.getString("stageId"),
            stageName = json.getString("stageName"),
            coordinateSystem = json.getString("coordinateSystem"),
            referenceImage = json.getString("referenceImage"),
            dataStatus = json.getString("dataStatus"),
            items = items
        )
        StageDatasetValidator.validate(dataset)
        return dataset
    }
}
