"""틱톡샵 공식 제품컷을 pid 로 받아 둔다.

상품 페이지의 og:image 가 1080x1080 공식 제품컷이다. 그 주소에는 서명값이
붙어 있어 시간이 지나면 막히므로, 링크로 걸지 않고 내려받아 저장한다.

받은 파일은 web/public/top/<pid>.jpg 로 떨어지고, web/data/top10.json 의
'이미지' 칸이 그에 맞춰 갱신된다. 못 받은 제품은 null 로 둔다 —
화면에서는 빈 자리로 나온다.

가끔 퍼즐 CAPTCHA 가 뜨는 제품이 있다. 라이브 전용처럼 공개 페이지가
없는 상품이 그렇다. 우회하지 않는다. 그런 제품은 사람이 셀러센터에서
받아 web/public/top/<pid>.jpg 로 넣어 주고 이 스크립트를 다시 돌리면 된다.

사용: python shop_images.py [pid ...]    (인자 없으면 top10.json 전체)
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


def fetch_one(pid):
    """제품컷을 받아 저장한다. 받으면 파일 크기를, 못 받으면 까닭을 돌려준다."""
    html = get(f"https://shop.tiktok.com/view/product/{pid}")
    if 막힘.search(html):
        raise RuntimeError("봇 차단 화면 — 사람이 셀러센터에서 받아야 한다")
    m = OG_IMAGE.search(html)
    if not m:
        raise RuntimeError("og:image 가 없다")
    im = Image.open(io.BytesIO(get(unescape(m.group(1)), binary=True)))
    원본 = im.size
    im = im.convert("RGB")
    if max(im.size) > LONG_EDGE:
        im.thumbnail((LONG_EDGE, LONG_EDGE), Image.LANCZOS)
    path = os.path.join(IMG_DIR, f"{pid}.jpg")
    im.save(path, "JPEG", quality=86, optimize=True)
    return f"{원본[0]}x{원본[1]} → {im.size[0]}px, {os.path.getsize(path)//1024}KB"


def main():
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
            print(f"  {i:>2}/{len(want)} {pid} {fetch_one(pid)}")
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
