"""드라이브 교안 PPTX 를 내려받아 텍스트를 뽑고, 글자 없는 슬라이드의 이미지만 따로 뽑는다.

폴더가 '링크가 있는 모든 사용자'로 공개돼 있어야 동작한다. 커넥터의 파일
다운로드는 base64 로 대화창에 들어오기 때문에 수십 MB 교안에는 못 쓴다.
그래서 여기서는 공개 링크로 직접 받는다(디스크로 바로 떨어진다).

100MB 가 넘는 파일은 구글이 바이러스 검사 확인 페이지를 한 번 끼워 넣기
때문에, 그 페이지에서 confirm 토큰을 뽑아 다시 요청해야 한다.

사용: python fetch.py [제품명 일부 ...]   (인자 없으면 manifest 전체)
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PPTX_DIR = os.path.join(HERE, "pptx")
IMG_DIR = os.path.join(HERE, "images")
OUT = os.path.join(HERE, "decks.json")

UA = "Mozilla/5.0"
# 슬라이드에 글자가 이것밖에 없으면 '사실상 빈 슬라이드'로 본다.
BOILERPLATE = re.compile(r"본 문구는 화장품법|^특징|^제형|^사용방법|^추천 피부|^\d+$|^STEP|^Before$|^After$")


def curl(url, out, extra=()):
    subprocess.run(
        ["curl", "-sS", "-L", "--max-time", "600", "-A", UA, "-c", "/tmp/gck", "-b", "/tmp/gck",
         *extra, "-o", out, url],
        check=True,
    )


def download(file_id, dest):
    """공개 링크로 PPTX 를 받는다. 큰 파일의 확인 페이지도 처리한다."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    curl(url, dest)
    with open(dest, "rb") as f:
        head = f.read(4)
    if head[:2] == b"PK":                      # 정상적인 pptx(zip)
        return True

    # HTML 이 돌아왔다면 확인 페이지다. confirm 토큰을 뽑아 다시 요청한다.
    html = open(dest, encoding="utf-8", errors="ignore").read()
    token = re.search(r'name="confirm"\s+value="([^"]+)"', html) or \
            re.search(r"confirm=([0-9A-Za-z_-]+)", html)
    uuid = re.search(r'name="uuid"\s+value="([^"]+)"', html)
    if not token:
        return False
    url = (f"https://drive.usercontent.google.com/download?id={file_id}"
           f"&export=download&confirm={token.group(1)}")
    if uuid:
        url += f"&uuid={uuid.group(1)}"
    curl(url, dest)
    with open(dest, "rb") as f:
        return f.read(2) == b"PK"


def sparse_slides(deck):
    """글자가 거의 없는데 이미지가 있는 슬라이드 = 수치가 그림 안에만 있는 슬라이드."""
    out = []
    for s in deck["slides"]:
        meaningful = [b for b in s["text"] if not BOILERPLATE.search(b.strip())]
        chars = sum(len(b) for b in meaningful)
        if s["images"] and chars < 40:
            out.append(s["no"])
    return out


def dump_slide_images(pptx, slide_nos, outdir):
    """지정한 슬라이드의 이미지를 원본 그대로 꺼낸다."""
    import zipfile
    os.makedirs(outdir, exist_ok=True)
    written = []
    with zipfile.ZipFile(pptx) as z:
        for n in slide_nos:
            rels = f"ppt/slides/_rels/slide{n}.xml.rels"
            if rels not in z.namelist():
                continue
            rmap = dict(re.findall(r'Id="([^"]+)"[^>]*Target="\.\./media/([^"]+)"',
                                   z.read(rels).decode("utf8")))
            xml = z.read(f"ppt/slides/slide{n}.xml").decode("utf8")
            for i, rid in enumerate(re.findall(r'r:embed="([^"]+)"', xml), 1):
                name = rmap.get(rid)
                if not name:
                    continue
                data = z.read("ppt/media/" + name)
                if len(data) < 20000:      # 아이콘·로고는 읽을 게 없다
                    continue
                path = os.path.join(outdir, f"s{n:02d}_{i}{os.path.splitext(name)[1]}")
                open(path, "wb").write(data)
                written.append(path)
    return written


def main():
    import extract  # 같은 폴더의 추출기 재사용

    manifest = json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))
    decks = manifest["decks"]
    if sys.argv[1:]:
        want = [a.lower() for a in sys.argv[1:]]
        decks = [d for d in decks if any(w in d["en"].lower() for w in want)]

    os.makedirs(PPTX_DIR, exist_ok=True)
    results = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else []
    done = {r["product"] for r in results}

    for d in decks:
        if d["en"] in done:
            print(f"⏭  {d['en']} (이미 처리)")
            continue
        dest = os.path.join(PPTX_DIR, d["id"] + ".pptx")
        if not (os.path.exists(dest) and open(dest, "rb").read(2) == b"PK"):
            print(f"⬇  {d['en']} ({d['mb']}MB) …", flush=True)
            if not download(d["id"], dest):
                print(f"❌ {d['en']}: 다운로드 실패(확인 페이지 처리 불가)")
                continue
        try:
            r = extract.extract(dest)
        except Exception as e:  # noqa: BLE001
            print(f"❌ {d['en']}: 추출 실패 {e}")
            continue
        r["product"] = d["en"]           # 파일명 추론보다 manifest 를 믿는다
        r["driveId"] = d["id"]
        r["빈슬라이드"] = sparse_slides(r)
        imgs = dump_slide_images(dest, r["빈슬라이드"], os.path.join(IMG_DIR, d["id"]))
        r["빈슬라이드이미지"] = imgs
        results.append(r)
        json.dump(results, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"✅ {d['en']}: 슬라이드 {r['slideCount']}장 / "
              f"글자없는 슬라이드 {len(r['빈슬라이드'])}장 → 이미지 {len(imgs)}개")

    print(f"\n💾 {OUT} — 교안 {len(results)}개")


if __name__ == "__main__":
    main()
