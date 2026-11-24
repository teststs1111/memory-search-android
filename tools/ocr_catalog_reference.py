#!/usr/bin/env python3
"""OCR annotated chapter reference labels and map text boxes to catalog names."""
from __future__ import annotations
import argparse, csv, difflib, io, json, re, subprocess
from pathlib import Path
from collections import defaultdict
import cv2
from detect_label_frames import align_annotated_to_base

def norm(s: str) -> str:
    return re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠ー]", "", s).lower()

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
    h,w=base.shape[:2]; scale=4
    enlarged=cv2.resize(aligned,(w*scale,h*scale),interpolation=cv2.INTER_CUBIC)
    gray=cv2.cvtColor(enlarged,cv2.COLOR_BGR2GRAY)
    temp=Path("/tmp/chapter-ocr.png"); cv2.imwrite(str(temp),gray)
    try:
        proc=subprocess.run(["tesseract",str(temp),"stdout","-l","jpn","--psm","11","tsv"],check=True,capture_output=True,text=True,encoding="utf-8")
    finally: temp.unlink(missing_ok=True)
    groups=defaultdict(list)
    for row in csv.DictReader(io.StringIO(proc.stdout),delimiter="\\t"):
        txt=(row.get("text") or "").strip()
        try:
            conf=float(row["conf"]); x,y,bw,bh=(int(row[k]) for k in ("left","top","width","height"))
        except (ValueError,KeyError): continue
        if txt and conf>=0 and bw>0 and bh>0:
            groups[(row.get("block_num"),row.get("par_num"),row.get("line_num"))].append((txt,conf,x,y,bw,bh))
    lines=[]
    for words in groups.values():
        txt="".join(x[0] for x in words)
        if not norm(txt): continue
        lines.append({"text":txt,"confidence":round(sum(x[1] for x in words)/len(words),1),
          "bounds":{"left":min(x[2] for x in words)//scale,"top":min(x[3] for x in words)//scale,
          "right":(max(x[2]+x[4] for x in words)+scale-1)//scale,
          "bottom":(max(x[3]+x[5] for x in words)+scale-1)//scale}})
    cat=json.loads(a.catalog.read_text(encoding="utf-8"))
    stage=next(x for x in cat["chapters"] if x["stageId"]==a.stage_id)
    ranked=[]
    for li,line in enumerate(lines):
        q=norm(line["text"])
        for idx,name in enumerate(stage["itemNames"]):
            score=difflib.SequenceMatcher(None,q,norm(name)).ratio()
            if score>=0.30: ranked.append((score,li,idx))
    ranked.sort(reverse=True)
    used_lines=set(); used_items=set(); matches=[None]*len(lines)
    for score,li,idx in ranked:
        if li in used_lines or idx in used_items: continue
        matches[li]={"itemId":f"{a.stage_id}_item_{idx+1:02d}","itemName":stage["itemNames"][idx],"similarity":round(score,3)}
        used_lines.add(li); used_items.add(idx)
    preview=base.copy()
    for i,line in enumerate(lines):
        b=line["bounds"]; match=matches[i]
        color=(40,220,40) if match and match["similarity"]>=0.65 else (0,210,255)
        cv2.rectangle(preview,(b["left"],b["top"]),(b["right"],b["bottom"]),color,2)
        label=match["itemName"] if match else line["text"][:12]
        cv2.putText(preview,label,(b["left"],max(14,b["top"]-3)),cv2.FONT_HERSHEY_SIMPLEX,0.35,color,1,cv2.LINE_AA)
    result={"stageId":a.stage_id,"purpose":"ocr_text_position_catalog_diagnostic_only","runtimeEnabled":False,
      "imageSize":{"width":w,"height":h},"lineCount":len(lines),
      "matchedCatalogCount":len(used_items),"highConfidenceMatchCount":sum(1 for m in matches if m and m["similarity"]>=0.65),
      "unmatchedCatalogItems":[{"itemId":f"{a.stage_id}_item_{i+1:02d}","itemName":name} for i,name in enumerate(stage["itemNames"]) if i not in used_items],
      "lines":[dict(line,match=matches[i]) for i,line in enumerate(lines)]}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    a.preview.parent.mkdir(parents=True,exist_ok=True)
    if not cv2.imwrite(str(a.preview),preview): raise RuntimeError("Could not write preview")
if __name__=="__main__": main()
