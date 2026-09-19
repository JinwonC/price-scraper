"""decks.json(교안 텍스트) + image-reads.json(이미지 판독) → products.json.

교안 28개가 같은 템플릿을 쓰기 때문에 슬라이드 제목과 번호 매긴 스펙 줄을
기준으로 기계적으로 가를 수 있다. 억지로 요약하지 않고 원문을 살려서 담는다.
비어 있는 항목은 채우지 않고 비운 채로 둔다 — 없는 걸 지어내지 않기 위해서.
"""

import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

# 번호 매긴 스펙 줄. "1. 상품명: ...", "2.출시월 : ..." 같은 변형을 모두 받는다.
SPEC_LINE = re.compile(r"^\s*\d+\s*[.)]\s*([가-힣A-Za-z /]{1,12}?)\s*[::]\s*(.*)$")
SPEC_KEY = {
    "상품명": "이름", "품명": "이름", "제품명": "이름",
    "출시월": "출시", "출시일": "출시", "리뉴얼 시점": "리뉴얼",
    "용량 및 가격": "용량가격", "용량 / 가격": "용량가격", "용량/가격": "용량가격",
    "가격": "용량가격", "용량": "용량가격",
    "기능성": "기능성", "타겟": "타겟",
}

# 슬라이드를 성격별로 가르는 제목 단서
SECTION_HINTS = [
    ("사용법", ("사용방법", "How to use", "사용 방법", "howtouse")),
    ("추천", ("추천 피부", "Recommend", "이런 분들")),
    ("성분", ("성분", "Ingredients")),
    ("시험", ("Tested", "인체적용시험", "임상", "in vitro")),
    ("제형", ("제형", "TEXTURE", "Texture")),
    ("기술", ("Technology", "기술")),
    ("향", ("향", "Fragrance")),
    ("용기", ("플립캡", "용기", "패키지")),
]

CLAIM = re.compile(r"\d+(?:\.\d+)?\s*%|인체적용시험|in ?vitro|임상|테스트 완료|특허\s*제?\s*[\d-]+호|ppm|PPM")
NOISE = re.compile(r"^(본 문구는 화장품법|\*본 문구|\d+$|Before$|After$|STEP\s*$)")

# 줄 앞에 붙은 글머리 기호. 화면에 그대로 내보내면 지저분하다.
BULLET = re.compile(r"^\s*(?:[-–•*]\s*|[①②③④⑤⑥⑦⑧⑨⑩]\s*|\d+\s*[.)]\s*)+")


def clean_line(text):
    return BULLET.sub("", text).strip()


def norm(text):
    """중복 판정을 위한 정규화. 공백·기호를 털어낸 알맹이만 남긴다."""
    return re.sub(r"[\s\-–•*()\[\]:：,·]", "", clean_line(text))


def slug(en):
    s = unicodedata.normalize("NFKD", en).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)


# 교안 슬라이드 제목은 "특징_ 성분 설명 Ingredients" 처럼 분류 접두어와 영문 라벨이
# 붙어 있다. 화면에는 알맹이만 보여 준다.
TITLE_PREFIX = re.compile(r"^(특징|제형|사용방법|사용법|추천\s*피부|플립캡)\s*[_\-–]*\s*")
TITLE_SUFFIX = re.compile(
    r"\s*[_\-–]?\s*(Ingredients|Check\s*point|How\s*to\s*use|Recommend|Tested|TEXTURE|"
    r"Technology|Fragrance)\s*$",
    re.IGNORECASE,
)


# 슬라이드 라벨일 뿐 정보가 없는 제목들. 섹션 이름을 그대로 반복하므로 버린다.
# ("성분 설명" 이 27번, "사용법" 이 17번 나오는 식이었다)
JUNK_TITLES = {
    "성분설명", "성분설명main", "베이스성분설명", "베이스메인성분설명", "캡슐성분설명",
    "성분urgrade", "제형", "제형설명", "향", "향설명", "향설명fragnance",
    "사용법", "사용방법", "기술", "기술자료", "임상", "추천", "추천사용자",
    "인체적용시험결과", "인체적용시험&invitro결과", "인체적용시험및테스트",
}

# 사내 링크·목록처럼 화면에 내보낼 것이 아닌 슬라이드
INTERNAL = re.compile(r"단서조항|Google Sheets|인체적용시험\s*(진행\s*)?LIST", re.IGNORECASE)


# "성분 설명 Ingredients_콜라겐 세럼 베이스" 처럼 라벨 뒤에 알맹이가 붙는 경우
LEAD_LABEL = re.compile(
    r"^(성분\s*설명|향\s*설명|제형\s*설명)\s*(Ingredients|Fragrance)?\s*[_\-–:]?\s*",
    re.IGNORECASE,
)


def pretty_title(title, fallback=""):
    """슬라이드 제목에서 알맹이만 남긴다. 알맹이가 없으면 빈 문자열."""
    t = TITLE_SUFFIX.sub("", TITLE_PREFIX.sub("", title.strip())).strip(" _-–*")
    stripped = LEAD_LABEL.sub("", t).strip(" _-–*()")
    if len(stripped) > 1:
        t = stripped
    if len(t) < 2 or re.sub(r"[\s_\-–*()]", "", t).lower() in JUNK_TITLES:
        return fallback
    return t


def real_title(slide):
    """각주가 첫 블록으로 잡혀 제목 자리를 차지한 슬라이드가 많다. 진짜 제목을 고른다."""
    for b in slide["text"]:
        b = b.strip()
        if b and not NOISE.match(b):
            return b.split("\n")[0][:80]
    return ""


def classify(title):
    for name, hints in SECTION_HINTS:
        if any(h.lower() in title.lower() for h in hints):
            return name
    return None


# 제목이 없어도 본문으로 사용법 슬라이드임을 알아볼 수 있는 표현
HOWTO_BODY = re.compile(r"발라\s*줍니다|발라줍니다|사용해\s*주세요|분사한? 후|두드려 흡수|덜어내어|도포하여")


def parse_spec(deck):
    """앞쪽 슬라이드에서 번호 매긴 스펙 줄을 긁는다."""
    spec, 니즈 = {}, []
    for s in deck["slides"][:7]:
        for block in s["text"]:
            lines = block.split("\n")
            for i, line in enumerate(lines):
                m = SPEC_LINE.match(line)
                if not m:
                    continue
                label, value = m.group(1).strip(), m.group(2).strip()
                key = SPEC_KEY.get(label)
                if key and value and key not in spec:
                    spec[key] = value
                if "개발배경" in label or "개발배경" in line:
                    니즈.extend(
                        re.sub(r"^\s*\d+\s*[.)]\s*", "", l).strip()
                        for l in lines[i + 1:] if l.strip()
                    )
            if "개발배경" in block and not 니즈:
                tail = block.split("개발배경", 1)[1]
                니즈.extend(
                    re.sub(r"^\s*\d+\s*[.)]\s*", "", l).strip()
                    for l in tail.split("\n")[1:] if l.strip()
                )
    니즈 = [clean_line(n) for n in dict.fromkeys(니즈)]
    니즈 = [n for n in dict.fromkeys(니즈) if len(n) > 5 and not SPEC_LINE.match(n)]
    return spec, 니즈


def parse_positioning(deck):
    """해시태그가 붙은 한 줄 포지셔닝 블록."""
    for s in deck["slides"][:4]:
        for block in s["text"]:
            if "#" in block:
                lines = [l.strip() for l in block.split("\n") if l.strip()]
                tags = [t for l in lines for t in re.findall(r"#\S+", l)]
                body = " ".join(l for l in lines if not l.startswith("#"))
                return {"문구": body, "태그": tags}
    return None


def parse_features(deck):
    """[제품 특징 및 베네핏] 블록을 ①②③ 단위로 가른다."""
    for s in deck["slides"][:6]:
        for block in s["text"]:
            if "제품 특징" not in block:
                continue
            body = block.split("]", 1)[1] if "]" in block else block
            parts = re.split(r"(?=[①②③④⑤⑥⑦⑧⑨⑩])", body)
            out = []
            for p in parts:
                p = p.strip()
                if len(p) < 6:
                    continue
                lines = [l.strip() for l in p.split("\n") if l.strip()]
                out.append({"제목": clean_line(lines[0]),
                            "설명": [clean_line(l) for l in lines[1:]]})
            if out:
                return out

    # Pro2X 처럼 '[제품 특징 및 베네핏]' 없이 'Point 1.' 형식을 쓰는 교안도 있다.
    out, seen = [], set()
    for s in deck["slides"]:
        t = real_title(s)
        if not re.match(r"Point\s*\d", t):
            continue
        head = re.sub(r"^Point\s*\d+\.?\s*", "", t)
        if head in seen:
            continue
        seen.add(head)
        body = [b.strip() for b in s["text"] if b.strip() and not NOISE.match(b.strip())][1:]
        out.append({"제목": head, "설명": body[:6]})
    return out


def parse_sections(deck):
    """슬라이드를 성격별로 모은다. 원문을 그대로 들고 간다."""
    buckets = {}
    for s in deck["slides"]:
        title = real_title(s)
        body = [b.strip() for b in s["text"] if b.strip() and not NOISE.match(b.strip())]
        kind = classify(title)
        if not kind and body and HOWTO_BODY.search(" ".join(body)):
            # 제목은 없지만 본문이 사용 안내인 슬라이드. 추정이라고 표시해 둔다.
            kind = "사용법"
            title = title or "사용 안내"
        if not kind:
            continue
        if INTERNAL.search(title):
            continue
        rest = body[1:] if body and body[0][:80] == title else body
        rest = [clean_line(l) for l in rest if not INTERNAL.search(l)]
        # 본문 안에 섞여 있는 슬라이드 라벨("특징_ 성분 설명 Ingredients",
        # "특징_인체적용시험")도 걷어낸다. 짧은 한 줄짜리 분류표만 지운다.
        rest = [
            l for l in rest
            if "\n" in l or (len(l) > 40 or not TITLE_PREFIX.match(l))
        ]
        if not rest and not s["tables"]:
            continue
        buckets.setdefault(kind, []).append({
            "슬라이드": s["no"],
            "제목": pretty_title(title),  # 라벨뿐이면 빈 문자열 — 화면에서 머리글을 뺀다
            "내용": rest,
            "표": s["tables"],
        })
    return buckets


def parse_claims(deck, 이미표시):
    """수치·시험 문장.

    예전에는 % 가 들어간 줄을 전부 담았더니 '11.76% 함유', '200,000PPM' 같은
    파편이 수십 줄 쌓이고, 그나마도 특징·성분 섹션에 이미 나온 말의 반복이었다.
    그래서 (1) 글머리 기호를 털고 (2) 너무 짧은 조각을 버리고 (3) 다른 섹션에
    이미 나온 문장은 제외한다. 슬라이드 번호는 출처 확인용으로 남긴다.
    """
    seen, out = set(), []
    for s in deck["slides"]:
        for block in s["text"]:
            for raw in block.split("\n"):
                line = clean_line(raw)
                if len(line) < 9 or NOISE.match(line) or not CLAIM.search(line):
                    continue
                key = norm(line)
                if not key or key in seen:
                    continue
                # 다른 섹션에 이미 통째로 나온 말이면 중복이다.
                if any(key in t for t in 이미표시):
                    continue
                seen.add(key)
                out.append({"슬라이드": s["no"], "문장": line})
    return out


def main():
    decks = json.load(open(os.path.join(HERE, "decks.json"), encoding="utf-8"))
    reads = json.load(open(os.path.join(HERE, "image-reads.json"), encoding="utf-8"))
    matching = json.load(open(os.path.join(HERE, "matching.json"), encoding="utf-8"))
    ko_by_en = {m["en"]: m["ko"] for m in matching["매칭됨"]}
    ko_by_en["Pro2X"] = matching["신제품_출시예정"][0]["ko"]

    products = []
    for deck in decks:
        en = deck["product"]
        spec, 니즈 = parse_spec(deck)
        read = reads.get(en, {})
        특징 = parse_features(deck)
        섹션 = parse_sections(deck)
        # 수치 문장이 위 섹션들과 겹치지 않도록, 이미 화면에 나오는 문장을 모아 둔다.
        이미표시 = {norm(t) for t in 니즈}
        이미표시 |= {norm(l) for f in 특징 for l in [f["제목"], *f["설명"]]}
        이미표시 |= {norm(l) for items in 섹션.values() for it in items for l in it["내용"]}
        # 슬라이드 제목은 섹션 머리글로 이미 보인다. 수치 문장으로 또 나오면 안 된다.
        이미표시 |= {norm(real_title(s)) for s in deck["slides"]}
        이미표시.discard("")
        p = {
            "slug": slug(en),
            "en": en,
            "ko": spec.get("이름") or ko_by_en.get(en, ""),
            "driveId": deck["driveId"],
            "스펙": spec,
            "니즈": 니즈,
            "포지셔닝": parse_positioning(deck),
            "특징": 특징,
            "섹션": 섹션,
            "수치문장": parse_claims(deck, 이미표시),
            "시험": read.get("tests", []),
            "문서": read.get("facts", []),
            "이미지메모": read.get("images", []),
            "사용법이미지": read.get("howto"),
            "용기메모": read.get("notes", []),
            "슬라이드수": deck["slideCount"],
            "판독대상슬라이드": deck["빈슬라이드"],
            # 분류에 안 잡힌 내용까지 확인할 수 있도록 원문을 통째로 같이 싣는다.
            "원문": [
                {"no": s["no"], "제목": real_title(s),
                 "내용": [b.strip() for b in s["text"] if b.strip() and not NOISE.match(b.strip())],
                 "표": s["tables"], "이미지수": s["images"]}
                for s in deck["slides"]
            ],
        }
        # 무엇이 비었는지 제품마다 명시해 둔다. 사이트에서 '교안에 없음'으로 보여주기 위함.
        p["없는항목"] = [k for k, v in {
            "용량·가격": spec.get("용량가격"), "출시/리뉴얼": spec.get("출시") or spec.get("리뉴얼"),
            "기능성": spec.get("기능성"), "타겟": spec.get("타겟"),
            "제품 특징": p["특징"], "사용법": p["섹션"].get("사용법"),
            "성분 설명": p["섹션"].get("성분"), "추천 대상": p["섹션"].get("추천"),
        }.items() if not v]
        products.append(p)

    products.sort(key=lambda x: x["ko"] or x["en"])
    out = os.path.join(HERE, "products.json")
    json.dump(products, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"제품 {len(products)}개 → {out}\n")
    for p in products:
        gaps = ", ".join(p["없는항목"]) or "-"
        print(f"  {p['ko'][:34]:<34} 특징{len(p['특징']):2d} 수치{len(p['수치문장']):3d} "
              f"시험{len(p['시험']):2d} | 없음: {gaps}")


if __name__ == "__main__":
    main()
