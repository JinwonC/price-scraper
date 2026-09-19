"""고른 이미지를 web/public/products/ 로 내보낸다. 웹용으로 줄이고 다시 압축한다."""
import json, os, shutil
from PIL import Image

HERE=os.path.dirname(os.path.abspath(__file__))
WEB="/home/user/price-scraper/web/public/products"
picks=json.load(open(os.path.join(HERE,"picks.json"),encoding="utf-8"))

if os.path.exists(WEB): shutil.rmtree(WEB)
os.makedirs(WEB)

manifest={}; total=0
for slug,items in picks.items():
    if slug.startswith("_"): continue
    out=os.path.join(WEB,slug); os.makedirs(out,exist_ok=True)
    rows=[]
    for i,(n,caption) in enumerate(items,1):
        src=os.path.join(HERE,"cand",slug,f"{n}.jpg")
        if not os.path.exists(src):
            print(f"  ! 없음 {slug}#{n}"); continue
        im=Image.open(src).convert("RGB")
        im.thumbnail((1100,1400))
        fn=f"{i:02d}.jpg"
        p=os.path.join(out,fn)
        im.save(p,quality=80,optimize=True,progressive=True)
        total+=os.path.getsize(p)
        rows.append({"src":f"/products/{slug}/{fn}","설명":caption,"w":im.width,"h":im.height})
    manifest[slug]=rows

json.dump(manifest,open(os.path.join(HERE,"images-manifest.json"),"w",encoding="utf-8"),
          ensure_ascii=False,indent=1)
print(f"제품 {len(manifest)}개 / 이미지 {sum(len(v) for v in manifest.values())}장 / "
      f"합계 {total/1048576:.1f}MB")
