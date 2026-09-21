"""고른 이미지를 web/public/products/ 로 내보낸다. 웹용으로 줄이고 다시 압축한다.

00.jpg 는 여기서 만들지 않는다. 틱톡샵 공식 제품컷이고 shop_images.py 가 받는다.
그래서 폴더를 통째로 지우지 않고 교안에서 나온 01 부터만 지웠다 다시 쓴다.
(예전에는 shutil.rmtree 로 폴더째 지워서, 다시 돌리면 공식 컷이 전부 날아갔다.)

shop-shots.json 의 '뺀픽' 은 공식 컷이 교안의 같은 제품컷을 대신한 자리다.
그 번호의 픽은 내보내지 않는다. 번호는 그대로 두어 02, 03 … 이 밀리지 않는다.
"""
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web", "public", "products")
picks = json.load(open(os.path.join(HERE, "picks.json"), encoding="utf-8"))
shots = json.load(open(os.path.join(HERE, "shop-shots.json"), encoding="utf-8"))["제품"]

manifest = {}
total = 0
공식 = 0
for slug, items in picks.items():
    if slug.startswith("_"):
        continue
    out = os.path.join(WEB, slug)
    os.makedirs(out, exist_ok=True)
    # 교안에서 나온 것만 지운다. 00.jpg 는 건드리지 않는다.
    for fn in os.listdir(out):
        if fn != "00.jpg" and fn.endswith(".jpg"):
            os.remove(os.path.join(out, fn))

    rows = []
    관 = os.path.join(out, "00.jpg")
    if os.path.exists(관):
        im = Image.open(관)
        rows.append({"src": f"/products/{slug}/00.jpg", "설명": "제품 컷",
                     "w": im.width, "h": im.height})
        total += os.path.getsize(관)
        공식 += 1

    뺄것 = set(shots.get(slug, {}).get("뺀픽", []))
    for i, (n, caption) in enumerate(items, 1):
        if i in 뺄것:
            continue
        src = os.path.join(HERE, "cand", slug, f"{n}.jpg")
        if not os.path.exists(src):
            print(f"  ! 없음 {slug}#{n}")
            continue
        im = Image.open(src).convert("RGB")
        im.thumbnail((1100, 1400))
        fn = f"{i:02d}.jpg"
        p = os.path.join(out, fn)
        im.save(p, quality=80, optimize=True, progressive=True)
        total += os.path.getsize(p)
        rows.append({"src": f"/products/{slug}/{fn}", "설명": caption,
                     "w": im.width, "h": im.height})
    manifest[slug] = rows

json.dump(manifest, open(os.path.join(HERE, "images-manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
없음 = [s for s in manifest if not os.path.exists(os.path.join(WEB, s, "00.jpg"))]
print(f"제품 {len(manifest)}개 / 이미지 {sum(len(v) for v in manifest.values())}장 / "
      f"합계 {total/1048576:.1f}MB / 공식 제품컷 {공식}개")
if 없음:
    print("공식 제품컷이 없는 제품 (shop_images.py --edu 로 받는다):")
    for s in 없음:
        print("  -", s)
