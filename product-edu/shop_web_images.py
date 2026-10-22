"""받아 둔 틱톡샵 이미지를 사이트에 걸 크기로 줄여 web/public/shop 으로 옮긴다.

shop_gallery.py 가 받아 둔 원본은 한 제품에 30MB 가까이 된다. 저장소에 그대로
넣을 수 없어서, 화면에 걸릴 크기(긴 변 900px)로 줄이고 WebP 로 바꿔 둔다.
제품컷은 캐러셀 한 칸이 900px 를 넘지 않는다.

원본은 저장소 밖에 둔 채로 두고, 여기서 나온 것만 커밋한다.

사용:
  python shop_web_images.py --src /tmp/shop-images [--edge 900] [--quality 80]
"""

import argparse
import collections
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")
OUT_DIR = os.path.join(WEB, "public", "shop")
OUT_JSON = os.path.join(WEB, "data", "shop-images.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="shop_gallery.py 가 받아 둔 폴더")
    ap.add_argument("--edge", type=int, default=900)
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()

    # 폴더를 그대로 훑는다. 파일 이름이 곧 차례다 — g = 갤러리, d = 상세.
    받은것 = collections.OrderedDict()
    for slug in sorted(os.listdir(a.src)):
        방 = os.path.join(a.src, slug)
        if not os.path.isdir(방):
            continue
        받은것[slug] = sorted(
            f for f in os.listdir(방) if f[0] in "gd" and not f.startswith(".")
        )

    # 이미 넣어 둔 제품 목록에 덧붙인다. 단품과 세트를 따로 돌릴 수 있게.
    제품 = collections.OrderedDict()
    if os.path.exists(OUT_JSON):
        제품 = json.load(open(OUT_JSON, encoding="utf-8"),
                        object_pairs_hook=collections.OrderedDict).get("제품", collections.OrderedDict())
    총바이트, 장수 = 0, 0
    for slug, 파일들 in 받은것.items():
        갤러리, 상세 = [], []
        for 파일 in 파일들:
            원본 = os.path.join(a.src, slug, 파일)
            if not os.path.exists(원본):
                continue
            이름 = os.path.splitext(파일)[0] + ".webp"
            방 = os.path.join(OUT_DIR, slug)
            os.makedirs(방, exist_ok=True)
            둘곳 = os.path.join(방, 이름)

            im = Image.open(원본).convert("RGB")
            if max(im.size) > a.edge:
                im.thumbnail((a.edge, a.edge), Image.LANCZOS)
            im.save(둘곳, "WEBP", quality=a.quality, method=5)
            총바이트 += os.path.getsize(둘곳)
            장수 += 1

            칸 = collections.OrderedDict([
                ("src", f"/shop/{slug}/{이름}"),
                ("w", im.size[0]),
                ("h", im.size[1]),
            ])
            (갤러리 if 파일.startswith("g") else 상세).append(칸)

        제품[slug] = collections.OrderedDict([("갤러리", 갤러리), ("상세", 상세)])
        print(f"  {slug[:46]:<48} 갤러리 {len(갤러리):>2} · 상세 {len(상세):>2}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(collections.OrderedDict([
            ("_주", "틱톡샵 상품 페이지에서 받은 제품 이미지. 교안 화면 맨 아래 "
                    "캐러셀로 건다. 갤러리는 정사각 제품컷, 상세는 상세페이지 컷이다."),
            ("_크기", f"긴 변 {a.edge}px WebP. 원본(장당 1~3MB)은 저장소에 넣지 않는다 "
                    f"— product-edu/shop_gallery.py 로 언제든 다시 받는다."),
            ("제품", 제품),
        ]), f, ensure_ascii=False, indent=1)
        f.write("\n")

    print(f"\n제품 {len(제품)}개 · 이미지 {장수}장 · {총바이트/1024/1024:.1f}MB → web/public/shop")


if __name__ == "__main__":
    main()
