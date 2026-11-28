#!/usr/bin/env python3
"""Validate and render Chapter 10 review-only coordinate candidates."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHAPTER_DIR = ROOT / "reference" / "chapter_10"
DATASET = ROOT / "app/src/main/assets/stages/chapter_10_label_boxes.candidates.json"
RUNTIME_DATASET = ROOT / "app/src/main/assets/stages/chapter_10.json"
CATALOG = ROOT / "app/src/main/assets/stages/item_catalogs.json"
BASE_IMAGE = CHAPTER_DIR / "base.jpg"
ANNOTATED_IMAGE = CHAPTER_DIR / "annotated.jpg"
OUTPUT = CHAPTER_DIR / "label_box_candidates.jpg"
COMPARISON = CHAPTER_DIR / "label_box_comparison.jpg"

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def compute_alignment(annotated: np.ndarray, base: np.ndarray):
    sift = cv2.SIFT_create(nfeatures=12000)
    gray_a = cv2.cvtColor(annotated, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    keypoints_a, descriptors_a = sift.detectAndCompute(gray_a, None)
    keypoints_b, descriptors_b = sift.detectAndCompute(gray_b, None)
    if descriptors_a is None or descriptors_b is None:
        raise SystemExit("Could not extract features from both Chapter 10 references")
    pairs = cv2.BFMatcher().knnMatch(descriptors_a, descriptors_b, k=2)
    good = [first for first, second in pairs if first.distance < 0.72 * second.distance]
    if len(good) < 1000:
        raise SystemExit(f"Insufficient image matches: {len(good)}")
    points_a = np.float32([keypoints_a[m.queryIdx].pt for m in good])
    points_b = np.float32([keypoints_b[m.trainIdx].pt for m in good])
    matrix, inlier_mask = cv2.findHomography(points_a, points_b, cv2.RANSAC, 3.0)
    if matrix is None or inlier_mask is None:
        raise SystemExit("Could not align annotated and clean Chapter 10 references")
    inliers = int(inlier_mask.sum())
    ratio = inliers / len(good)
    if inliers < 1000 or ratio < 0.90:
        raise SystemExit(f"Weak source alignment: {inliers}/{len(good)} inliers ({ratio:.3f})")
    return matrix, len(good), inliers, ratio

def map_rect(rect: list[int], matrix: np.ndarray) -> list[float]:
    x1, y1, x2, y2 = rect
    corners = np.float32([[x1,y1],[x2,y1],[x2,y2],[x1,y2]]).reshape(-1,1,2)
    mapped = cv2.perspectiveTransform(corners, matrix).reshape(-1,2)
    return [float(mapped[:,0].min()),float(mapped[:,1].min()),float(mapped[:,0].max()),float(mapped[:,1].max())]

def overlap_pairs(items: list[dict]) -> list[list[str]]:
    result=[]
    for index, first in enumerate(items):
        a=first.get("bounds")
        if a is None: continue
        for second in items[index+1:]:
            b=second.get("bounds")
            if b is None: continue
            ow=max(0.0,min(a["right"],b["right"])-max(a["left"],b["left"]))
            oh=max(0.0,min(a["bottom"],b["bottom"])-max(a["top"],b["top"]))
            if ow*oh>0: result.append([first["itemName"],second["itemName"]])
    return result

def validate_candidate_data(data,runtime,catalog,annotated,base):
    if data.get("runtimeEnabled") is not False or data.get("dataStatus")!="partially_reviewed_candidate_only":
        raise SystemExit("Chapter 10 candidate data must remain runtime-disabled")
    if runtime.get("dataStatus")!="awaiting_coordinate_verification" or runtime.get("items")!=[]:
        raise SystemExit("Chapter 10 runtime dataset must remain pending and empty")
    height,width=base.shape[:2]
    ah,aw=annotated.shape[:2]
    if (width,height)!=(data["actualReferenceImageSize"]["width"],data["actualReferenceImageSize"]["height"]):
        raise SystemExit("Clean-base dimensions do not match provenance")
    if (aw,ah)!=(data["actualAnnotatedImageSize"]["width"],data["actualAnnotatedImageSize"]["height"]):
        raise SystemExit("Annotated dimensions do not match provenance")
    source=data["sourceImage"]
    if sha256(ANNOTATED_IMAGE)!=source["annotatedSha256"] or sha256(BASE_IMAGE)!=source["baseSha256"]:
        raise SystemExit("Chapter 10 source SHA-256 mismatch")
    names=next(ch["itemNames"] for ch in catalog["chapters"] if ch["stageId"]=="chapter_10")
    items=data["items"]
    if [item["itemName"] for item in items]!=names:
        raise SystemExit("Candidate names/order differ from Chapter 10 catalog")
    ids=[item["itemId"] for item in items]
    if len(ids)!=len(set(ids)): raise SystemExit("Candidate item IDs are not unique")
    matrix,good,inliers,ratio=compute_alignment(annotated,base)
    expected=np.asarray(data["referenceImageAlignment"]["annotatedToBaseHomography"])
    if np.max(np.abs(matrix-expected))>0.005:
        raise SystemExit("Recomputed source homography differs from recorded provenance")
    basis=data["imageSize"]
    for item in items:
        rect=item.get("sourceRect")
        if rect is None:
            if item.get("bounds") is not None or item.get("annotatedSourceRect") is not None or item.get("mappedBaseRect") is not None:
                raise SystemExit(f"{item['itemName']}: missing item must not have coordinates")
            if item.get("visualReviewStatus")!="catalog_item_not_found_in_reference":
                raise SystemExit(f"{item['itemName']}: missing-item status is inconsistent")
            continue
        x1,y1,x2,y2=rect
        if not (0<=x1<x2<=basis["width"] and 0<=y1<y2<=basis["height"]):
            raise SystemExit(f"{item['itemName']}: sourceRect is outside 563x1000 basis")
        expected_bounds={"left":x1/basis["width"],"top":y1/basis["height"],"right":x2/basis["width"],"bottom":y2/basis["height"]}
        for key,value in expected_bounds.items():
            if abs(item["bounds"][key]-value)>1e-6: raise SystemExit(f"{item['itemName']}: {key} differs from sourceRect")
        mapped=map_rect(item["annotatedSourceRect"],matrix)
        recorded=item["mappedBaseRect"]
        if max(abs(mapped[i]-recorded[i]) for i in range(4))>2.0:
            raise SystemExit(f"{item['itemName']}: mappedBaseRect differs from homography")
        mapped_basis=[mapped[0]/width*basis["width"],mapped[1]/height*basis["height"],mapped[2]/width*basis["width"],mapped[3]/height*basis["height"]]
        if max(abs(mapped_basis[i]-rect[i]) for i in range(4))>1.5:
            raise SystemExit(f"{item['itemName']}: sourceRect differs from mapped label bounds")
    edge={i["itemName"] for i in items if i.get("visualReviewStatus")=="edge_clipped_pending_full_bounds"}
    near={i["itemName"] for i in items if i.get("visualReviewStatus")=="near_edge_alignment_pending"}
    missing={i["itemName"] for i in items if i.get("visualReviewStatus")=="catalog_item_not_found_in_reference"}
    review=data["visualReview"]
    if edge!={"トランシーバー","ロープ","レンチ"} or near!={"木片"} or missing!={"バケツ"}:
        raise SystemExit("Chapter 10 pending-item classification is inconsistent")
    complete=sum(i.get("sourceRect") is not None for i in items)-len(edge)-len(near)
    if complete!=30 or review["visuallyGroundedCompleteCount"]!=30:
        raise SystemExit("Chapter 10 complete-box count is inconsistent")
    if review["edgeClippedCandidateCount"]!=3 or review["nearEdgeCandidateCount"]!=1 or review["missingCatalogItemNames"]!=["バケツ"]:
        raise SystemExit("Chapter 10 review counts are inconsistent")
    if overlap_pairs(items)!=review["overlappingCandidatePairs"]:
        raise SystemExit("Chapter 10 overlap review list is stale")
    blue=next(i for i in items if i["itemName"]=="青いバケツ")
    if blue.get("referenceTextLines")!=["バケツ","青"]:
        raise SystemExit("Blue-bucket two-line reference notation is missing")
    return matrix,good,inliers,ratio

def draw_candidates(image,items):
    rendered=image.copy()
    height,width=rendered.shape[:2]
    for index,item in enumerate(items,1):
        mapped=item.get("mappedBaseRect")
        if mapped is None: continue
        x1,y1,x2,y2=[int(round(v)) for v in mapped]
        status=item.get("visualReviewStatus")
        color=(0,140,255) if status=="edge_clipped_pending_full_bounds" else (0,220,255) if status=="near_edge_alignment_pending" else (0,220,40)
        cv2.rectangle(rendered,(x1,y1),(x2,y2),color,3,cv2.LINE_AA)
        mx=min(max(x1+14,14),width-15); my=min(max(y1+14,14),height-15)
        cv2.circle(rendered,(mx,my),13,(20,20,20),-1,cv2.LINE_AA)
        cv2.putText(rendered,str(index),(mx-5,my+5),cv2.FONT_HERSHEY_SIMPLEX,0.42,(255,255,255),1,cv2.LINE_AA)
    return rendered

def main():
    data=json.loads(DATASET.read_text(encoding="utf-8"))
    runtime=json.loads(RUNTIME_DATASET.read_text(encoding="utf-8"))
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
    base=cv2.imread(str(BASE_IMAGE),cv2.IMREAD_COLOR)
    annotated=cv2.imread(str(ANNOTATED_IMAGE),cv2.IMREAD_COLOR)
    if base is None or annotated is None: raise SystemExit("Could not read both original Chapter 10 references")
    matrix,good,inliers,ratio=validate_candidate_data(data,runtime,catalog,annotated,base)
    height,width=base.shape[:2]
    aligned=cv2.warpPerspective(annotated,matrix,(width,height))
    annotated_overlay=draw_candidates(aligned,data["items"])
    base_overlay=draw_candidates(base,data["items"])
    if not cv2.imwrite(str(OUTPUT),base_overlay,[cv2.IMWRITE_JPEG_QUALITY,95]):
        raise SystemExit("Could not write Chapter 10 clean-base preview")
    crop_top=700
    crop_height=height-crop_top
    gap=16
    header=78
    canvas=np.full((crop_height+header,width*2+gap,3),245,dtype=np.uint8)
    canvas[header:,:width]=annotated_overlay[crop_top:height,:,:]
    canvas[header:,width+gap:]=base_overlay[crop_top:height,:,:]
    cv2.putText(canvas,"ANNOTATED SOURCE ALIGNED TO CLEAN BASE + CANDIDATE BOXES",(12,27),cv2.FONT_HERSHEY_SIMPLEX,0.52,(25,25,25),2,cv2.LINE_AA)
    cv2.putText(canvas,"CLEAN BASE + SAME MAPPED CANDIDATE BOXES",(width+gap+12,27),cv2.FONT_HERSHEY_SIMPLEX,0.52,(25,25,25),2,cv2.LINE_AA)
    cv2.putText(canvas,"30 complete / 3 edge-pending / 1 near-edge / 1 catalog-missing",(12,54),cv2.FONT_HERSHEY_SIMPLEX,0.46,(40,40,40),1,cv2.LINE_AA)
    cv2.putText(canvas,f"SIFT/RANSAC alignment: {inliers}/{good} inliers ({ratio:.3f})",(width+gap+12,54),cv2.FONT_HERSHEY_SIMPLEX,0.46,(40,40,40),1,cv2.LINE_AA)
    if not cv2.imwrite(str(COMPARISON),canvas,[cv2.IMWRITE_JPEG_QUALITY,94]):
        raise SystemExit("Could not write Chapter 10 comparison preview")
    print(f"Chapter 10: {len(data['items'])} catalog entries; 30 complete, 3 edge-clipped pending, 1 near-edge pending, 1 missing; {len(data['visualReview']['overlappingCandidatePairs'])} AABB overlaps recorded. Runtime dataset remains empty and disabled.")

if __name__=="__main__":
    main()
