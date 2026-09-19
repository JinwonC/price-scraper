"""제품별 이미지 후보 시트. 사람이 눈으로 고르기 위한 것."""
import json, os, re, zipfile, io
from PIL import Image, ImageDraw

HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(HERE,"sheets"); os.makedirs(OUT,exist_ok=True)
CAND=os.path.join(HERE,"cand");  os.makedirs(CAND,exist_ok=True)

prods=json.load(open(os.path.join(HERE,"products.json"),encoding="utf-8"))
index={}
for p in prods:
    path=os.path.join(HERE,"pptx",p["driveId"]+".pptx")
    if not os.path.exists(path): continue
    picks=[]
    with zipfile.ZipFile(path) as z:
        media=[n for n in z.namelist() if n.startswith("ppt/media/")]
        for n in media:
            sz=z.getinfo(n).file_size
            if sz<60000: continue           # 아이콘·로고 제외
            try:
                im=Image.open(io.BytesIO(z.read(n))); im.load()
            except Exception: continue
            w,h=im.size
            if w<400 or h<400: continue     # 너무 작은 건 본문 장식
            picks.append((sz,n,w,h))
    picks.sort(reverse=True)
    picks=picks[:9]
    # 후보 파일로 저장
    saved=[]
    d=os.path.join(CAND,p["slug"]); os.makedirs(d,exist_ok=True)
    with zipfile.ZipFile(path) as z:
        for i,(sz,n,w,h) in enumerate(picks,1):
            im=Image.open(io.BytesIO(z.read(n))).convert("RGB")
            fn=os.path.join(d,f"{i}.jpg"); im.save(fn,quality=88)
            saved.append({"n":i,"src":n,"w":w,"h":h})
    # 시트 만들기
    if saved:
        cols=3; cell=330
        rows=(len(saved)+cols-1)//cols
        sheet=Image.new("RGB",(cols*cell,rows*cell),"white")
        dr=ImageDraw.Draw(sheet)
        for i,s in enumerate(saved):
            im=Image.open(os.path.join(d,f"{s['n']}.jpg"))
            im.thumbnail((cell-16,cell-34))
            x=(i%cols)*cell; y=(i//cols)*cell
            sheet.paste(im,(x+(cell-im.width)//2, y+26+(cell-34-im.height)//2))
            dr.rectangle([x+2,y+2,x+cell-2,y+cell-2],outline="#ccc")
            dr.text((x+10,y+7),f"#{s['n']}  {s['w']}x{s['h']}",fill="black")
        sheet.save(os.path.join(OUT,p["slug"]+".jpg"),quality=85)
    index[p["slug"]]={"ko":p["ko"],"후보":saved}
json.dump(index,open(os.path.join(HERE,"cand","index.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print(f"시트 {len(os.listdir(OUT))}개")
