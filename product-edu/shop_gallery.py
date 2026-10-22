"""틱톡샵 상품 페이지의 제품 이미지를 제품별로 모아 받는다.

shop_images.py 는 대표 컷 한 장(og:image)만 받는다. 이 스크립트는 상품
페이지에 붙어 있는 **갤러리 전체와 상세페이지 이미지**를 원본 해상도로 받는다.

어떻게 찾나:
  상품 페이지 HTML 안에 화면을 그릴 자료가 JSON 으로 함께 들어 있다.
  그 안의 `"images":[...]` 가 갤러리(정사각 제품컷)고, 그 밖에 흩어진
  이미지 블록이 상세페이지 컷이다. 가게 로고나 '무료배송' 같은 화면 장식은
  크기가 작아 걸러낸다.

원본 받기:
  주소에 붙은 `~tplv-...-resize-webp:800:600.webp` 는 줄여 놓은 판이다.
  그 자리를 `~tplv-...-origin-image.image` 로 바꾸면 올린 원본이 내려온다.
  서명값(쿼리)은 그대로 둬야 한다 — 떼면 400 이 난다.

받은 파일은 저장소에 넣지 않는다. 한 제품에 20장, 장당 2~3MB 라 저장소가
감당할 크기가 아니다. --out 으로 받을 자리를 정하고, 쓸 만큼만 따로 옮긴다.

사용:
  python shop_gallery.py --out <폴더> [슬러그 ...]
  python shop_gallery.py --out <폴더> --pids 1732... 1732...   (세트처럼 교안이 없는 상품)
  python shop_gallery.py --out <폴더> --max-edge 1600   # 줄여서 받기
"""

import argparse
import collections
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS_JSON = os.path.join(HERE, "shop-shots.json")

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
막힘 = re.compile(r"security check|captcha|verify_page", re.I)
# {"width":800,"height":800,"uri":"tos-…","url_list":["https://…"]}
블록 = re.compile(
    r'\{"width":(\d+),"height":(\d+),"uri":"([^"]+)","url_list":\["([^"]+)"'
)
# 화면 장식. 제품과 무관하다.
장식 = re.compile(r"tos-maliva-i-|/pdp-lockup|store_blue_v")
TPLV = re.compile(r"~tplv-([a-z0-9]+)-[^?]*")


def 되돌리기(s):
    return s.replace("\\u002F", "/").replace("\\u0026", "&")


def get(url, binary=False, 횟수=3):
    for i in range(횟수):
        r = subprocess.run(
            ["curl", "-sSL", "--max-time", "60", "-A", UA, url],
            capture_output=True,
        )
        if r.returncode == 0 and r.stdout:
            return r.stdout if binary else r.stdout.decode("utf-8", "replace")
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(r.stderr.decode()[:160] or "빈 응답")


def 갤러리자리(html):
    """`"images":[ … ]` 안쪽의 문자 범위. 갤러리와 상세를 가르는 데 쓴다."""
    i = html.find('"images":[')
    if i < 0:
        return (-1, -1)
    j = html.index("[", i)
    깊이, k = 0, j
    while k < len(html):
        if html[k] == "[":
            깊이 += 1
        elif html[k] == "]":
            깊이 -= 1
            if 깊이 == 0:
                return (j, k)
        k += 1
    return (j, len(html))


def 이미지들(html):
    """(종류, 가로, 세로, uri, 주소) 목록. 문서에 적힌 순서를 지킨다."""
    시작, 끝 = 갤러리자리(html)
    본것, out = set(), []
    for m in 블록.finditer(html):
        w, h, uri, url = int(m.group(1)), int(m.group(2)), 되돌리기(m.group(3)), 되돌리기(m.group(4))
        if 장식.search(uri) or max(w, h) < 400:
            continue
        if uri in 본것:
            continue
        본것.add(uri)
        종류 = "갤러리" if 시작 <= m.start() <= 끝 else "상세"
        out.append((종류, w, h, uri, url))
    return out


def 원본주소(url):
    """줄여 놓은 주소를 원본 주소로 바꾼다. 서명값은 그대로 둔다."""
    m = TPLV.search(url)
    if not m:
        return url
    return url[: m.start()] + f"~tplv-{m.group(1)}-origin-image.image" + url[m.end():]


def 확장자(b):
    if b[:3] == b"\xff\xd8\xff":
        return "jpg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "webp"
    return "bin"


def 재기(b):
    """가로세로를 돌려준다. Pillow 가 없으면 (0, 0)."""
    try:
        from PIL import Image
    except Exception:
        return (0, 0)
    try:
        return Image.open(io.BytesIO(b)).size
    except Exception:
        return (0, 0)


def 줄이기(b, 긴변):
    """사이트에 걸 만한 크기로 줄인다. Pillow 가 없으면 원본 그대로."""
    try:
        from PIL import Image
    except Exception:
        return b, "원본(줄이지 못함)"
    im = Image.open(io.BytesIO(b))
    본 = im.size
    if max(본) <= 긴변:
        return b, f"{본[0]}x{본[1]}"
    im = im.convert("RGB")
    im.thumbnail((긴변, 긴변), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88, optimize=True)
    return buf.getvalue(), f"{본[0]}x{본[1]} → {im.size[0]}x{im.size[1]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--pids", nargs="*", default=None,
                    help="교안이 없는 상품. 폴더 이름이 pid 가 된다")
    ap.add_argument("--out", required=True, help="받을 폴더 (저장소 밖에 둔다)")
    ap.add_argument("--max-edge", type=int, default=0,
                    help="긴 변을 이 크기로 줄여서 받는다. 0 이면 원본")
    a = ap.parse_args()

    if a.pids:
        # 교안이 없는 상품은 pid 를 그대로 폴더 이름으로 쓴다.
        shots = {pid: {"pid": pid} for pid in a.pids}
        want = list(shots)
    else:
        shots = json.load(open(SHOTS_JSON, encoding="utf-8"))["제품"]
        want = a.slugs or list(shots)
        모르는 = [s for s in want if s not in shots]
        if 모르는:
            sys.exit(f"shop-shots.json 에 없는 슬러그: {', '.join(모르는)}")

    목록, 실패, 총바이트 = collections.OrderedDict(), [], 0
    for i, slug in enumerate(want, 1):
        pid = shots[slug]["pid"]
        print(f"\n[{i}/{len(want)}] {slug}  (pid {pid})")
        try:
            html = get(f"https://shop.tiktok.com/us/pdp/x/{pid}")
            if 막힘.search(html):
                raise RuntimeError("봇 차단 화면 — 잠시 뒤 다시 돌린다")
            찾음 = 이미지들(html)
            if not 찾음:
                raise RuntimeError("이미지 블록을 못 찾았다 (페이지 구조가 바뀐 듯)")
        except Exception as e:
            print(f"   실패 — {e}")
            실패.append(slug)
            time.sleep(2)
            continue

        방 = os.path.join(a.out, slug)
        os.makedirs(방, exist_ok=True)
        줄들, 번호 = [], collections.Counter()
        for 종류, w, h, uri, url in 찾음:
            번호[종류] += 1
            머리 = "g" if 종류 == "갤러리" else "d"
            try:
                raw = get(원본주소(url), binary=True)
            except Exception as e:
                print(f"   {종류} {번호[종류]:02d} 실패 — {e}")
                continue
            본크기 = 재기(raw)
            if a.max_edge:
                raw, 적을크기 = 줄이기(raw, a.max_edge)
            else:
                적을크기 = f"{본크기[0]}x{본크기[1]}" if 본크기[0] else "?"
            이름 = f"{머리}{번호[종류]:02d}.{확장자(raw)}"
            with open(os.path.join(방, 이름), "wb") as f:
                f.write(raw)
            총바이트 += len(raw)
            줄들.append(collections.OrderedDict([
                ("파일", f"{slug}/{이름}"),
                ("종류", 종류),
                ("크기", 적을크기),
                ("uri", uri),
            ]))
            print(f"   {이름:<10} {종류}  {적을크기}  {len(raw)//1024}KB")
            time.sleep(0.4)
        목록[slug] = 줄들
        time.sleep(1.5)  # 몰아치면 막힌다

    with open(os.path.join(a.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(collections.OrderedDict([
            ("_주", "틱톡샵 상품 페이지에서 받은 제품 이미지 목록. "
                    "g = 갤러리(정사각 제품컷), d = 상세페이지 컷."),
            ("_받은때", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + " UTC"),
            ("제품", 목록),
        ]), f, ensure_ascii=False, indent=1)
        f.write("\n")

    장수 = sum(len(v) for v in 목록.values())
    print(f"\n제품 {len(목록)}개 · 이미지 {장수}장 · {총바이트/1024/1024:.0f}MB → {a.out}")
    for s in 실패:
        print(f"  못 받음: {s}")


if __name__ == "__main__":
    main()
