"""교안 PPTX → 구조화 JSON 추출기.

슬라이드별로 텍스트·표를 뽑고, 이미지는 개수와 위치만 기록한다.
(이미지 안의 수치는 대부분 텍스트 박스에도 있어서, 먼저 텍스트로 뽑아보고
 빠진 게 있을 때만 이미지 판독을 붙이는 순서가 비용이 싸다)

사용: python extract.py <pptx...> -o out.json
"""

import json
import os
import re
import sys
import zipfile

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

# 파일명이 깨져 들어와도 내용으로 제품을 알아보기 위한 단서
PRODUCT_HINTS = [
    ("Vita Toning Serum Toner", ["세럼 토너", "Serum Toner"]),
    ("Vita toning Capsule Serum", ["캡슐 세럼", "Capsule Serum"]),
    ("Vita toning Capsule Cream", ["캡슐 크림", "Capsule Cream"]),
    ("Vita toning Capsule Cleansing Oil", ["캡슐 토닝 클렌징 오일", "캡슐 클렌징 오일"]),
    ("Vita Toning Galvanic Wrinkle Eye Cream", ["갈바닉", "Galvanic"]),
    ("Vita Toning Anti-Aging Spray Serum 8%", ["안티에이징 스프레이 세럼"]),
    ("Waterfull UV Essence Sunscreen", ["에센스 선스크린", "에센스 선크림"]),
    ("White Truffle Waterfull Tone Up Sunscreen Serum", ["톤업 선스크린", "톤업 선크림"]),
    ("White Truffle Waterfull Mild Sun Cream", ["마일드 선스크린", "마일드 선크림"]),
    ("Air Fit Fresh Sun Stick", ["에어 핏", "Air Fit"]),
    ("White Truffle First Spray Serum", ["퍼스트 스프레이 세럼"]),
    ("White Truffle Vital Spray Serum", ["바이탈 스프레이 세럼"]),
    ("White Truffle Refresh Aqua Serum", ["리프레쉬 아쿠아"]),
    ("White truffle Return Oil Cream Cleanser", ["리턴 오일 크림 클렌저", "리턴 오일크림"]),
    ("White Truffle Double Serum All-in-one Multi Balm", ["올인원 멀티밤"]),
    ("Double Quick Liposome Serum Mask Pad", ["리포좀 세럼 마스크"]),
    ("First Oil Capsule Serum", ["퍼스트 오일 캡슐"]),
    ("White Truffle Double Serum & Cream 2-in-1", ["더블 세럼 앤 크림", "Double Serum & Cream"]),
    ("White Truffle Double Layer Revitalizing Serum", ["더블 레이어 리바이탈라이징"]),
    ("Italian White Truffle Professional Repairing Hair Perfume Serum", ["헤어 퍼퓸 세럼"]),
    ("Professional Repairing Hair Oil Serum", ["헤어 오일 세럼"]),
    ("White Truffle Intensive Volufiline Ampoule", ["인텐시브 보르피린 앰플"]),
    ("Intensive Vegan Volufiline Spray Ampoule", ["보르피린 스프레이 앰플"]),
    ("White Truffle Intensive Volufiline Grinding Cream", ["보르피린 그라인딩"]),
    ("White Truffle Moisturizing Serum Lotion", ["모이스처라이징 세럼 로션"]),
    ("Signature Vita Capsule Hydrogel Mask 8-Shape", ["하이드로겔 마스크"]),
    ("Signature Vita Collagen Pore Tightening Deep Cleansing Balm", ["딥 클렌징 밤", "딥클렌징 밤"]),
    ("d'Alba Signature Allthera Double Shot", ["올쎄라", "올쌔라"]),
    ("Pro2X", ["프로 투엑스", "Pro 2X", "프로투엑스"]),
]

# 임상·시험 수치가 들어 있는 문장을 따로 모은다(제일 많이 찾는 정보라서)
CLAIM_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*%|인체적용시험|in ?vitro|임상|테스트 완료|특허\s*제?\s*[\d-]+호")


def walk(shapes):
    """그룹 안에 든 도형까지 펼쳐서 순회한다.

    교안은 성분 설명 카드를 통째로 그룹으로 묶어 두는 일이 잦다. 최상위만
    훑으면 그 카드의 글자가 통째로 빠진다(벨기에 스파 워터 14%, LIPOCALM
    구성 성분 등이 실제로 이렇게 누락됐다).
    """
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk(shape.shapes)
        else:
            yield shape


def slide_text_blocks(slide):
    """슬라이드에서 텍스트 블록과 표를 순서대로 뽑는다."""
    blocks, tables = [], []
    for shape in walk(slide.shapes):
        if shape.has_text_frame:
            text = shape.text_frame.text.strip()
            if text:
                blocks.append(re.sub(r"\n{2,}", "\n", text))
        if getattr(shape, "has_table", False) and shape.has_table:
            tables.append([[c.text.strip() for c in row.cells] for row in shape.table.rows])
    return blocks, tables


def count_pictures(slide):
    return sum(1 for s in walk(slide.shapes) if s.__class__.__name__ == "Picture")


def media_stats(path):
    """PPTX 안의 이미지 개수·용량. PPTX 는 이미 zip 이라 압축 여지가 없다."""
    with zipfile.ZipFile(path) as z:
        media = [n for n in z.namelist() if n.startswith("ppt/media/")]
        total = sum(z.getinfo(n).file_size for n in media)
    return len(media), total


def guess_product(all_text):
    for en, hints in PRODUCT_HINTS:
        if any(h in all_text for h in hints):
            return en
    return None


def extract(path):
    prs = Presentation(path)
    slides = []
    for i, slide in enumerate(prs.slides, 1):
        blocks, tables = slide_text_blocks(slide)
        slides.append({
            "no": i,
            "title": blocks[0][:80] if blocks else "",
            "text": blocks,
            "tables": tables,
            "images": count_pictures(slide),
        })

    all_text = "\n".join(b for s in slides for b in s["text"])
    img_count, img_bytes = media_stats(path)

    return {
        "sourceFile": os.path.basename(path),
        "product": guess_product(all_text),
        "slideCount": len(slides),
        "imageCount": img_count,
        "imageBytes": img_bytes,
        "fileBytes": os.path.getsize(path),
        "claims": sorted({
            line.strip()
            for s in slides for b in s["text"] for line in b.split("\n")
            if CLAIM_PATTERN.search(line) and len(line.strip()) > 4
        }),
        "slides": slides,
    }


def main():
    args = [a for a in sys.argv[1:] if a != "-o"]
    out = "extracted.json"
    if "-o" in sys.argv:
        out = sys.argv[sys.argv.index("-o") + 1]
        args = [a for a in args if a != out]

    results = []
    for path in args:
        try:
            r = extract(path)
        except Exception as e:  # noqa: BLE001
            print(f"❌ {os.path.basename(path)}: {e}")
            continue
        results.append(r)
        pct = r["imageBytes"] / r["fileBytes"] * 100 if r["fileBytes"] else 0
        print(
            f"✅ {r['product'] or '(제품 미확인)'}\n"
            f"   슬라이드 {r['slideCount']}장 / 이미지 {r['imageCount']}개 "
            f"({r['fileBytes']/1048576:.1f}MB 중 이미지가 {pct:.0f}%)\n"
            f"   수치·시험 문장 {len(r['claims'])}개 추출"
        )

    json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n💾 {out} 저장 ({len(results)}개 교안)")


if __name__ == "__main__":
    main()
