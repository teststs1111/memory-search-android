import json
import sys
import unittest
from pathlib import Path
import cv2

ROOT=Path(__file__).resolve().parents[2]
STAGES=ROOT/"app/src/main/assets/stages"
sys.path.insert(0,str(ROOT/"tools"))
from render_chapter10_label_boxes import ANNOTATED_IMAGE,BASE_IMAGE,compute_alignment,overlap_pairs,sha256,validate_candidate_data

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

class Chapter10CandidateReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ANNOTATED_IMAGE.exists() or not BASE_IMAGE.exists():
            raise unittest.SkipTest("Chapter 10 source images are downloaded by its dedicated review workflow")
        cls.candidates=read_json(STAGES/"chapter_10_label_boxes.candidates.json")
        cls.runtime=read_json(STAGES/"chapter_10.json")
        cls.catalog=read_json(STAGES/"item_catalogs.json")
        cls.names=next(ch["itemNames"] for ch in cls.catalog["chapters"] if ch["stageId"]=="chapter_10")
        cls.annotated=cv2.imread(str(ANNOTATED_IMAGE),cv2.IMREAD_COLOR)
        cls.base=cv2.imread(str(BASE_IMAGE),cv2.IMREAD_COLOR)

    def test_candidate_names_and_ids_match_catalog_order(self):
        items=self.candidates["items"]
        self.assertEqual([i["itemName"] for i in items],self.names)
        ids=[i["itemId"] for i in items]
        self.assertEqual(len(ids),len(self.names))
        self.assertEqual(len(ids),len(set(ids)))

    def test_reference_dimensions_and_hashes_are_exact(self):
        data=self.candidates
        self.assertEqual(data["imageSize"],{"width":563,"height":1000})
        self.assertEqual(data["actualReferenceImageSize"],{"width":1404,"height":2496})
        self.assertEqual(data["actualAnnotatedImageSize"],{"width":2016,"height":2520})
        self.assertEqual(sha256(ANNOTATED_IMAGE),data["sourceImage"]["annotatedSha256"])
        self.assertEqual(sha256(BASE_IMAGE),data["sourceImage"]["baseSha256"])

    def test_runtime_dataset_stays_pending_and_empty(self):
        self.assertFalse(self.candidates["runtimeEnabled"])
        self.assertEqual(self.candidates["dataStatus"],"partially_reviewed_candidate_only")
        self.assertEqual(self.runtime["dataStatus"],"awaiting_coordinate_verification")
        self.assertEqual(self.runtime["items"],[])

    def test_source_rectangles_match_normalized_bounds(self):
        basis=self.candidates["imageSize"]
        for item in self.candidates["items"]:
            rect=item.get("sourceRect")
            if rect is None:
                self.assertIsNone(item.get("bounds"),item["itemName"])
                self.assertIsNone(item.get("annotatedSourceRect"),item["itemName"])
                continue
            x1,y1,x2,y2=rect
            self.assertTrue(0<=x1<x2<=basis["width"],item["itemName"])
            self.assertTrue(0<=y1<y2<=basis["height"],item["itemName"])
            expected={"left":x1/basis["width"],"top":y1/basis["height"],"right":x2/basis["width"],"bottom":y2/basis["height"]}
            for key,value in expected.items():
                self.assertAlmostEqual(item["bounds"][key],value,places=6,msg=item["itemName"])

    def test_edge_near_edge_and_missing_items_remain_pending(self):
        review=self.candidates["visualReview"]
        self.assertEqual(review["edgeClippedItemNames"],["トランシーバー","ロープ","レンチ"])
        self.assertEqual(review["nearEdgeItemNames"],["木片"])
        self.assertEqual(review["missingCatalogItemNames"],["バケツ"])
        self.assertEqual(review["visuallyGroundedCompleteCount"],30)
        self.assertEqual(review["edgeClippedCandidateCount"],3)
        self.assertEqual(review["nearEdgeCandidateCount"],1)
        items={i["itemName"]:i for i in self.candidates["items"]}
        self.assertIsNone(items["バケツ"]["sourceRect"])
        self.assertEqual(items["バケツ"]["source"],"not_found_in_annotated_reference")
        self.assertEqual(items["バケツ"]["status"],"pending_missing_reference_label")
        self.assertTrue(all(i.get("source")=="annotated" for i in self.candidates["items"] if i["itemName"]!="バケツ"))
        self.assertEqual(items["青いバケツ"]["referenceTextLines"],["バケツ","青"])

    def test_annotation_to_clean_alignment_reproduces_candidate_rectangles(self):
        matrix,good,inliers,ratio=compute_alignment(self.annotated,self.base)
        expected=self.candidates["referenceImageAlignment"]["annotatedToBaseHomography"]
        self.assertLess(max(abs(matrix[i,j]-expected[i][j]) for i in range(3) for j in range(3)),0.005)
        self.assertGreaterEqual(good,1000)
        self.assertGreaterEqual(inliers,1000)
        self.assertGreater(ratio,0.90)
        validate_candidate_data(self.candidates,self.runtime,self.catalog,self.annotated,self.base)

    def test_axis_aligned_overlaps_are_recorded_without_auto_correction(self):
        actual=overlap_pairs(self.candidates["items"])
        self.assertEqual(actual,self.candidates["visualReview"]["overlappingCandidatePairs"])
        self.assertEqual(len(actual),19)
        self.assertFalse(self.candidates["visualReview"]["detectorOutputUsedAsCoordinateSource"])

if __name__=="__main__":
    unittest.main()
