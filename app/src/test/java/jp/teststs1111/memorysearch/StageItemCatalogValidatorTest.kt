package jp.teststs1111.memorysearch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class StageItemCatalogValidatorTest {
    @Test
    fun acceptsSeparateChapterCatalogs() {
        val catalogs = listOf(
            StageItemCatalog("chapter_1", "第1章", listOf("マグカップ", "テディベア")),
            StageItemCatalog("chapter_2", "第2章", listOf("星型チャーム", "作業灯"))
        )
        StageItemCatalogValidator.validate(catalogs)
        assertEquals(2, catalogs.size)
    }

    @Test
    fun rejectsDuplicateChapterIds() {
        assertThrows(IllegalArgumentException::class.java) {
            StageItemCatalogValidator.validate(
                listOf(
                    StageItemCatalog("chapter_1", "第1章", listOf("マグカップ")),
                    StageItemCatalog("chapter_1", "別データ", listOf("テディベア"))
                )
            )
        }
    }

    @Test
    fun rejectsDuplicateNamesWithinChapter() {
        assertThrows(IllegalArgumentException::class.java) {
            StageItemCatalogValidator.validate(
                listOf(StageItemCatalog("chapter_1", "第1章", listOf("マグカップ", "マグカップ")))
            )
        }
    }

    @Test
    fun rejectsNamesThatCollideAfterOcrNormalization() {
        assertThrows(IllegalArgumentException::class.java) {
            StageItemCatalogValidator.validate(
                listOf(StageItemCatalog("chapter_1", "第1章", listOf("ＡＢＣ", "abc")))
            )
        }
    }

    @Test
    fun rejectsBlankNamesAndInvalidStageIds() {
        assertThrows(IllegalArgumentException::class.java) {
            StageItemCatalogValidator.validate(
                listOf(StageItemCatalog("chapter_1", "第1章", listOf(" ")))
            )
        }
        assertThrows(IllegalArgumentException::class.java) {
            StageItemCatalogValidator.validate(
                listOf(StageItemCatalog("chapter_zero", "不正", listOf("品物")))
            )
        }
    }
}
