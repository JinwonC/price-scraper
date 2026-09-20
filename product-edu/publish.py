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
    r"|\b\d{2,3},\d{3}\b"        # 40,000 — 세는 단위가 붙은 것은 세는수 가 빼 준다
    r"|소비자가"
    r"|한국콜마|코스맥스|제조업자|화장품제조업자|제조원"
    r"|\d{2,4}-\d{3,4}-\d{4}"    # 02-332-7727
    r"|심사번호|보고번호|성적서\s*번호"
    r"|works\.do|결과서\s*경로|drive\.google|docs\.google"  # 사내 문서 링크
    r"|이미지\s*(변경|교체)\s*예정|AI\s*생성\s*시안|광고\s*자문"  # 사내 메모
)

# 가격처럼 생겼지만 가격이 아닌 수들. 하나씩 확인하고 적어 둔 것만 통과시킨다.
# 목록에 없는 '00,000' 꼴은 전부 그물에 걸린다.
세는수 = {
    "40,000": "캡슐 개수 (100ml 기준)",
    "20,000": "캡슐 개수 (50ml 기준)",
    "13,000": "갈바닉 아이크림의 분당 진동 횟수",
}
세는수찾기 = re.compile(r"\b(?:" + "|".join(세는수) + r")\b")


def leaks_in(글):
    """검열 그물에 걸린 자리를 사람이 읽을 수 있게 돌려준다."""
    가린 = 세는수찾기.sub("", 글)
    return sorted({m.group(0) for m in LEAK.finditer(가린)})


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


# 브랜드가 교안을 돌려쓰면서 다른 제품 문구가 섞여 들어온 자리.
# '모공보다 467배 작다' 는 얼굴 제품 문구인데 헤어 교안에도 그대로 복사돼 있다.
# 그리고 이 비교 자체가 외부 논문에 실린 모공 평균값과 견준 것이지
# 제품을 재서 나온 값이 아니라, 제품 성능처럼 읽히면 오해를 준다.
특징고침 = {
    "italian-white-truffle-professional-repairing-hair-perfume-serum": {
        "drop": ["모공보다 467배"],
    },
    "professional-repairing-hair-oil-serum": {
        "drop": ["모공보다 467배"],
    },
    "white-truffle-double-serum-cream-2-in-1": {
        "replace": {
            "모공보다 467배 작은 사이즈로 빠르고 강력하게 전달되는 펩타이드 엑소좀":
            "나노 크기로 만들어 피부에 빠르게 전달되는 펩타이드 엑소좀",
        },
    },
    "pro2x": {
        "replace": {
            "모공보다 467배 작은 듀얼 엑소좀으로 더욱 깊어진 침투력":
            "나노 크기의 듀얼 엑소좀으로 더욱 깊어진 침투력",
        },
    },
}


def 다듬기(o):
    """교안에서 딸려 온 띄어쓰기 찌꺼기를 턴다.

    PPT 칸에서 긁어 온 글이라 두 칸 띄움, 줄바꿈, '닦아 내고 , 끌어' 처럼
    부호 앞에 붙은 공백이 그대로 남아 있다. 화면에 그대로 보인다.
    """
    if isinstance(o, dict):
        return {k: 다듬기(v) for k, v in o.items()}
    if isinstance(o, list):
        return [다듬기(v) for v in o]
    if not isinstance(o, str):
        return o
    s = re.sub(r"\s+", " ", o)
    s = re.sub(r"\s+([,.!?)])", r"\1", s)
    s = re.sub(r"([(])\s+", r"\1", s)
    # 교안에서 쉼표를 두 번 친 자리. '70%,, 쌀PDRN'
    s = re.sub(r",\s*(?=,)", "", s)
    # 닫는 괄호 안으로 들어간 쉼표. 다음 성분과 나누는 쉼표이니 괄호 밖으로 낸다.
    s = re.sub(r",\s*\)", "),", s)
    # '10,000ppm ,10종' 처럼 쉼표 뒤가 붙어 버린 자리. 숫자 자릿점은 건드리지 않는다.
    s = re.sub(r",(?=[^\s\d])", ", ", s)
    # 줄 끝에 남은 쉼표. '나이아신아마이드 20,000ppm,'
    s = re.sub(r"[,\s]+$", "", s)
    return s.strip()


def fix_features(slug, 특징):
    """제품에 맞지 않거나 오해를 주는 줄을 빼거나 고쳐 쓴다."""
    rule = 특징고침.get(slug)
    if not rule:
        return 특징
    drop = rule.get("drop", [])
    rep = rule.get("replace", {})
    out = []
    for f in 특징:
        설명 = [rep.get(l, l) for l in f["설명"] if not any(d in l for d in drop)]
        제목 = rep.get(f["제목"], f["제목"])
        if any(d in 제목 for d in drop):
            continue
        out.append({"제목": 제목, "설명": 설명})
    return out


def main():
    src = json.load(open(os.path.join(HERE, "products.json"), encoding="utf-8"))
    etc = json.load(open(os.path.join(HERE, "etc.json"), encoding="utf-8"))
    en = json.load(open(os.path.join(HERE, "en.json"), encoding="utf-8"))

    out, leaks, 기타없음, 영어없음 = [], [], [], []
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
            "특징": fix_features(slug, p["특징"]),
            "기타": etc.get(slug, {}).get("항목", []),
            "en판": en.get(slug, {}),
        }
        if not pub["기타"]:
            기타없음.append(slug)
        # 영어 화면이 빌 자리를 미리 알려준다.
        if not pub["en판"].get("특징") or not any(
            i.get("title") for i in pub["기타"]
        ):
            영어없음.append(slug)
        pub = 다듬기(pub)
        hits = leaks_in(json.dumps(pub, ensure_ascii=False))
        if hits:
            leaks.append((slug, hits[:6]))
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
    if 영어없음:
        print(f"\n영어를 아직 안 쓴 제품 {len(영어없음)}개:")
        for s2 in 영어없음:
            print("  -", s2)
    if leaks:
        print("\n!! 내보내면 안 될 내용이 남아 있다:")
        for slug, hits in leaks:
            print(f"  - {slug}: {hits}")
        raise SystemExit(1)
    print("\n검열 그물에 걸린 것 없음.")


if __name__ == "__main__":
    main()
