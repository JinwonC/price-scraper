"""틱톡샵 공식 제품컷을 pid 로 받아 둔다.

상품 페이지의 og:image 가 1080x1080 공식 제품컷이다. 그 주소에는 서명값이
붙어 있어 시간이 지나면 막히므로, 링크로 걸지 않고 내려받아 저장한다.

받은 파일은 web/public/top/<pid>.jpg 로 떨어지고, web/data/top10.json 의
'이미지' 칸이 그에 맞춰 갱신된다. 못 받은 제품은 null 로 둔다 —
화면에서는 빈 자리로 나온다.

주소는 두 가지를 차례로 시도한다. /view/product/<pid> 는 정식 주소로
넘겨 주는 짧은 주소인데, 제품에 따라 그 단계에서 퍼즐 CAPTCHA 를 띄운다.
정식 주소인 /us/pdp/<슬러그>/<pid> 로 바로 가면 같은 제품이 그냥 열린다.
슬러그는 실제로 쓰이지 않아 아무 값이나 넣어도 된다.

그래도 막히는 제품이 있으면 우회하지 않는다. 사람이 셀러센터에서 받아
web/public/top/<pid>.jpg 로 넣어 주고 이 스크립트를 다시 돌리면 된다.

사용:
  python shop_images.py [pid ...]     상위 10개용. web/public/top/<pid>.jpg
  python shop_images.py --edu [슬러그 ...]
                                      교안 제품용. web/public/products/<슬러그>/00.jpg
                                      pid 는 shop-shots.json 에서 읽는다
"""

import collections
import io
import json
import os
import re
import subprocess
import sys
import time

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")
TOP_JSON = os.path.join(WEB, "data", "top10.json")
IMG_DIR = os.path.join(WEB, "public", "top")
SHOTS_JSON = os.path.join(HERE, "shop-shots.json")
EDU_DIR = os.path.join(WEB, "public", "products")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
OG_IMAGE = re.compile(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"')
막힘 = re.compile(r"security check|captcha|verify_page", re.I)
# 썸네일 자리라 이 정도면 충분하다. 저장소가 공개라 무겁게 두지 않는다.
LONG_EDGE = 440


def unescape(s):
    for a, b in (("&amp;", "&"), ("&quot;", '"'), ("&#x27;", "'"),
                 ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    return s


def get(url, binary=False):
    r = subprocess.run(["curl", "-sSL", "--max-time", "40", "-A", UA, url],
                       capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode()[:160])
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def og_image_url(pid):
    """상품 페이지에서 제품컷 주소를 찾는다. 정식 주소를 먼저 두드린다."""
    막힌적 = False
    for url in (f"https://shop.tiktok.com/us/pdp/x/{pid}",
                f"https://shop.tiktok.com/view/product/{pid}"):
        html = get(url)
        if 막힘.search(html):
            막힌적 = True
            continue
        m = OG_IMAGE.search(html)
        if m:
            return unescape(m.group(1))
    if 막힌적:
        raise RuntimeError("봇 차단 화면 — 사람이 셀러센터에서 받아야 한다")
    raise RuntimeError("og:image 가 없다")


def fetch_one(pid, path, 줄일지=True):
    """제품컷을 받아 저장한다. 받으면 크기를, 못 받으면 까닭을 돌려준다."""
    im = Image.open(io.BytesIO(get(og_image_url(pid), binary=True)))
    원본 = im.size
    im = im.convert("RGB")
    # 상위 10개는 44px 썸네일 자리라 줄인다. 교안은 갤러리에 크게 걸려 원본을 쓴다.
    if 줄일지 and max(im.size) > LONG_EDGE:
        im.thumbnail((LONG_EDGE, LONG_EDGE), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "JPEG", quality=86 if 줄일지 else 88, optimize=True)
    본 = f"{원본[0]}x{원본[1]}"
    난 = f"{im.size[0]}x{im.size[1]}"
    꼬리 = f"{os.path.getsize(path)//1024}KB"
    return f"{본} → {난}, {꼬리}" if 본 != 난 else f"{본}, {꼬리}"


def 교안(인자):
    """교안 제품의 대표 제품컷을 web/public/products/<슬러그>/00.jpg 에 받는다."""
    shots = json.load(open(SHOTS_JSON, encoding="utf-8"))["제품"]
    want = 인자 or list(shots)
    모르는 = [s for s in want if s not in shots]
    if 모르는:
        sys.exit(f"shop-shots.json 에 없는 슬러그: {', '.join(모르는)}")

    실패 = []
    for i, slug in enumerate(want, 1):
        path = os.path.join(EDU_DIR, slug, "00.jpg")
        # 이미 받아 둔 것은 건드리지 않는다. 사람이 손으로 넣은 파일도 지키려는 것이다.
        if os.path.exists(path) and not 인자:
            print(f"  {i:>2}/{len(want)} {slug[:46]:<48} 이미 있음")
            continue
        try:
            print(f"  {i:>2}/{len(want)} {slug[:46]:<48} {fetch_one(shots[slug]['pid'], path, 줄일지=False)}")
        except Exception as e:
            print(f"  {i:>2}/{len(want)} {slug[:46]:<48} 실패 — {e}")
            실패.append(slug)
        time.sleep(1.6)  # 몰아치면 막힌다

    있음 = sum(1 for s in shots if os.path.exists(os.path.join(EDU_DIR, s, "00.jpg")))
    print(f"\n대표 제품컷 {있음}/{len(shots)} 개.")
    for s in 실패:
        print(f"  못 받음: {s}")
    if 실패:
        print("  다시 돌리거나, 셀러센터에서 받아 00.jpg 로 넣으면 된다.")


def main():
    if sys.argv[1:2] == ["--edu"]:
        return 교안(sys.argv[2:])
    os.makedirs(IMG_DIR, exist_ok=True)
    data = json.load(open(TOP_JSON, encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)
    항목 = data["항목"]
    want = sys.argv[1:] or [it["pid"] for it in 항목]

    받음, 실패 = 0, []
    for i, pid in enumerate(want, 1):
        # 이미 받아 둔 것은 건드리지 않는다. 사람이 손으로 넣은 파일도 지키려는 것이다.
        if os.path.exists(os.path.join(IMG_DIR, f"{pid}.jpg")) and not sys.argv[1:]:
            print(f"  {i:>2}/{len(want)} {pid} 이미 있음")
            받음 += 1
            continue
        try:
            print(f"  {i:>2}/{len(want)} {pid} {fetch_one(pid, os.path.join(IMG_DIR, f'{pid}.jpg'))}")
            받음 += 1
        except Exception as e:
            print(f"  {i:>2}/{len(want)} {pid} 실패 — {e}")
            실패.append(pid)
        time.sleep(1.6)  # 몰아치면 막힌다

    for it in 항목:
        p = os.path.join(IMG_DIR, f"{it['pid']}.jpg")
        it["이미지"] = f"/top/{it['pid']}.jpg" if os.path.exists(p) else None
    with open(TOP_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    붙음 = sum(1 for it in 항목 if it["이미지"])
    print(f"\n제품컷 {붙음}/{len(항목)} 개가 붙었다.")
    for pid in 실패:
        print(f"  못 받음: {pid}")


if __name__ == "__main__":
    main()
