#!/usr/bin/env python3
"""OCR catalog labels from annotation-only regions; diagnostics remain review-only."""
from __future__ import annotations
import argparse, difflib, json, re, subprocess, tempfile
from pathlib import Path
import cv2
import numpy as np
from detect_label_frames import align_annotated_to_base, make_annotation_difference_mask

def norm(s: str) -> str:
    return re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠ー]", "", s).lower()

def ocr_crop(image):
    scale=3
    enlarged=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
    # Keep the original label colors and outline: grayscale alone loses contrast
    # between the white glyph fill and black stroke on translucent backgrounds.
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        cv2.imwrite(tmp.name,enlarged)
        proc=subprocess.run(["tesseract",tmp.name,"stdout","-l","jpn","--psm","6"],
          check=True,capture_output=True,text=True,encoding="utf-8")
    return re.sub(r"\s+","",proc.stdout).strip()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--image",type=Path,required=True)
    p.add_argument("--base",type=Path,required=True)
    p.add_argument("--catalog",type=Path,required=True)
    p.add_argument("--stage-id",required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--preview",type=Path,required=True)
    a=p.parse_args()
    base=cv2.imread(str(a.base)); annotated=cv2.imread(str(a.image))
    if base is None or annotated is None: raise ValueError("Could not load reference images")
    aligned=align_annotated_to_base(annotated,base)
    h,w=base.shape[:2]
    mask=make_annotation_difference_mask(aligned,base)
    # Annotation fills are solid connected regions, unlike unrelated scene text.
    # A small close repairs JPEG gaps without merging distant/touching labels.
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,
      cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)),iterations=1)
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    regions=[]
    min_area=max(100,int(w*h*0.00004))
    max_area=int(w*h*0.08)
    for i in range(1,count):
        x,y,bw,bh,area=map(int,stats[i])
        if area<min_area or area>max_area or bw<12 or bh<10: continue
        pad=max(3,int(min(bw,bh)*0.06))
        x1,y1=max(0,x-pad),max(0,y-pad)
        x2,y2=min(w,x+bw+pad),min(h,y+bh+pad)
        text=ocr_crop(aligned[y1:y2,x1:x2])
        if text:
            regions.append({"text":text,"confidence":None,
              "bounds":{"left":x1,"top":y1,"right":x2,"bottom":y2},
              "annotationArea":area})
    cat=json.loads(a.catalog.read_text(encoding="utf-8"))
    stage=next(x for x in cat["chapters"] if x["stageId"]==a.stage_id)
    ranked=[]
    for li,line in enumerate(regions):
        q=norm(line["text"])
        if not q: continue
        for idx,name in enumerate(stage["itemNames"]):
            target=norm(name)
            score=difflib.SequenceMatcher(None,q,target).ratio()
            # Avoid assigning short OCR fragments to unrelated short names.
            if score>=0.52 and (len(q)>=2 or q==target): ranked.append((score,li,idx))
    ranked.sort(reverse=True)
    used_lines=set(); used_items=set(); matches=[None]*len(regions)
    for score,li,idx in ranked:
        if li in used_lines or idx in used_items: continue
        matches[li]={"itemId":f"{a.stage_id}_item_{idx+1:02d}",
          "itemName":stage["itemNames"][idx],"similarity":round(score,3)}
        used_lines.add(li); used_items.add(idx)
    preview=base.copy()
    for i,line in enumerate(regions):
        b=line["bounds"]; match=matches[i]
        color=(40,220,40) if match and match["similarity"]>=0.72 else (0,210,255)
        cv2.rectangle(preview,(b["left"],b["top"]),(b["right"],b["bottom"]),color,2)
        label=match["itemName"] if match else line["text"][:12]
        cv2.putText(preview,label,(b["left"],max(14,b["top"]-3)),cv2.FONT_HERSHEY_SIMPLEX,0.35,color,1,cv2.LINE_AA)
    result={"stageId":a.stage_id,"purpose":"ocr_text_position_catalog_diagnostic_only",
      "runtimeEnabled":False,"imageSize":{"width":w,"height":h},
      "regionCount":len(regions),"matchedCatalogCount":len(used_items),
      "highConfidenceMatchCount":sum(1 for m in matches if m and m["similarity"]>=0.72),
      "unmatchedCatalogItems":[{"itemId":f"{a.stage_id}_item_{i+1:02d}","itemName":name}
        for i,name in enumerate(stage["itemNames"]) if i not in used_items],
      "regions":[dict(line,match=matches[i]) for i,line in enumerate(regions)]}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    a.preview.parent.mkdir(parents=True,exist_ok=True)
    if not cv2.imwrite(str(a.preview),preview): raise RuntimeError("Could not write preview")
if __name__=="__main__": main()
