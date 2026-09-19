"""교안 추출본(products.json)에서 웹에 내보낼 것만 골라 web/data/products.json 을 만든다.

교안은 사내 자료라 크리에이터에게 보여선 안 되는 것이 섞여 있다.
여기서 한 번 걸러내고, 걸러낸 뒤의 내용만 사이트로 나간다.

빼는 것
  - 가격, 소비자가 변경 이력, '미정' 같은 가격 협의 흔적
  - 출시·리뉴얼 예정일 (아직 안 나온 제품의 계획)
  - 제조사, 화장품제조업자, 소비자 상담 전화번호
  - 인증서·시험성적서 번호, 심사번호, 보고번호
  - 슬라이드 원문과 섹션 원문 통째 (전성분 나열, 사내 메모가 그대로 들어 있다)

남기는 것
  - 용량, 기능성, 타겟
  - 포지셔닝 문구와 해시태그, [제품 특징 및 베네핏]
  - 사람이 직접 쓴 브리프(briefs.json)와 기타(etc.json)

기타는 원문을 그대로 싣지 않는다. 사람이 읽고 풀어 쓴 문장만 들어간다.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(HERE), "web", "data")

# 용량가격 은 '150ml / 40,000원' 처럼 붙어 있다. 앞의 용량만 남긴다.
CAPACITY = re.compile(
    r"\d+(?:\.\d+)?\s*(?:ml|mL|ML|g|G|매|ea|EA)\b"
    r"(?:\s*\(NET\s*WT\.?[^)]*\))?"
    r"(?:\s*\*\s*\d+\s*ea)?",
)

# 내보내기 전 마지막으로 훑는 그물. 여기 걸리면 사람이 다시 봐야 한다.
LEAK = re.compile(
    r"[\d,]{4,}\s*원"           # 39,500원
    r"|\b\d{2,3},\d{3}\b"        # 40,000
    r"|소비자가"
    r"|한국콜마|코스맥스|제조업자|화장품제조업자|제조원"
    r"|\d{2,4}-\d{3,4}-\d{4}"    # 02-332-7727
    r"|심사번호|보고번호|성적서\s*번호"
)


def capacity_only(값):
    """'100ml(29,000원→29,900원)' → '100ml'. 용량을 못 찾으면 통째로 버린다."""
    if not 값:
        return None
    found = CAPACITY.findall(값)
    if not found:
        return None
    # 50ml / 100ml 처럼 두 가지 용량이 있는 제품은 둘 다 남긴다.
    seen, out = set(), []
    for f in found:
        f = re.sub(r"\s+", " ", f).strip()
        if f.lower() not in seen:
            seen.add(f.lower())
            out.append(f)
    return " · ".join(out)


def main():
    src = json.load(open(os.path.join(HERE, "products.json"), encoding="utf-8"))
    etc = json.load(open(os.path.join(HERE, "etc.json"), encoding="utf-8"))

    out, leaks, 기타없음 = [], [], []
    for p in src:
        slug = p["slug"]
        pub = {
            "slug": slug,
            "en": p["en"],
            "ko": p["ko"],
            "스펙": {
                k: v
                for k, v in {
                    "용량": capacity_only(p["스펙"].get("용량가격")),
                    "기능성": p["스펙"].get("기능성"),
                    "타겟": p["스펙"].get("타겟"),
                }.items()
                if v
            },
            "포지셔닝": p["포지셔닝"],
            "특징": p["특징"],
            "기타": etc.get(slug, {}).get("항목", []),
        }
        if not pub["기타"]:
            기타없음.append(slug)
        hits = LEAK.findall(json.dumps(pub, ensure_ascii=False))
        if hits:
            leaks.append((slug, sorted(set(hits))[:6]))
        out.append(pub)

    path = os.path.join(WEB, "products.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")

    kb = os.path.getsize(path) / 1024
    print(f"제품 {len(out)}개 → {path} ({kb:.0f}KB)")
    if 기타없음:
        print(f"\n기타를 아직 안 쓴 제품 {len(기타없음)}개:")
        for s in 기타없음:
            print("  -", s)
    if leaks:
        print("\n!! 내보내면 안 될 내용이 남아 있다:")
        for slug, hits in leaks:
            print(f"  - {slug}: {hits}")
        raise SystemExit(1)
    print("\n검열 그물에 걸린 것 없음.")


if __name__ == "__main__":
    main()
