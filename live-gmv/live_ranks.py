"""라이브에서 많이 팔린 제품 순위를 만든다 (브랜드 라이브 + 크리에이터 라이브 합산).

왜 CRUVA 가 아니라 시트인가:
  CRUVA 의 제품별 live_gmv 는 크리에이터(제휴) 라이브만 센다. 브랜드 자체
  라이브는 제품별 내역이 아예 내려오지 않는다. 제품별로 브랜드 라이브가
  적힌 곳은 '제품별 유입매출 RAW' 탭의 G 열(Seller LIVE-attributed GMV)
  뿐이다. 그래서 이 순위만 시트에서 뽑는다.

무엇을 내보내나:
  순위와 pid·제품명·슬러그뿐이다. **금액은 파일에도, 로그에도 쓰지 않는다.**
  이 저장소는 공개고 Actions 로그도 누구나 읽는다.

기간:
  시트가 수동 탭이라 며칠 밀릴 수 있다. 그래서 '오늘' 이 아니라 시트에
  적힌 마지막 날짜를 끝으로 잡고 거기서 30일을 거슬러 센다. 화면에는
  '언제까지 집계' 를 같이 적는다.

환경변수:
  GOOGLE_CREDENTIALS  서비스 계정 JSON (필수)
  SRC_SHEET_ID        원본 스프레드시트 ID (필수)
  SRC_TAB             원본 탭 이름. 없으면 '유입매출' 이 든 탭을 찾는다
  DAYS                며칠을 셀지 (기본 30)
  TOP_N               순위에 실을 제품 수 (기본 10)
"""

import collections
import datetime
import json
import os
import re
import sys

from live_gmv import (
    CREATOR_COL,
    PID,
    SELLER_COL,
    env,
    find_header,
    pick_tab,
    to_date,
    to_num,
)

import gspread

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "web", "data", "live-ranks.json")
TOP_JSON = os.path.join(ROOT, "web", "data", "top10.json")
TIKTOK_JSON = os.path.join(ROOT, "product-edu", "tiktok-us.json")
IMG_DIR = os.path.join(ROOT, "web", "public", "top")


def 이름다듬기(s):
    """'[OFFICIAL d'Alba] White Truffle First Spray Serum - Authentic ...' → 앞부분만."""
    s = re.sub(r"^\s*\[OFFICIAL[^\]]*\]\s*", "", str(s or "").strip())
    s = s.split(" - ")[0].strip()
    return re.sub(r"\s+", " ", s)


def 슬러그표():
    """pid → 교안 슬러그. 교안이 없는 세트·기획 구성은 안 들어 있다."""
    try:
        d = json.load(open(TIKTOK_JSON, encoding="utf-8"))
    except OSError:
        return {}
    표 = {}
    for slug, v in d.items():
        if slug.startswith("_") or not isinstance(v, dict):
            continue
        pid = str(v.get("product_id") or "").strip()
        if pid:
            표[pid] = slug
    return 표


def main():
    src_id = env("SRC_SHEET_ID", required=True)
    days = int(env("DAYS", "30"))
    n = int(env("TOP_N", "10"))

    gc = gspread.service_account_from_dict(
        json.loads(env("GOOGLE_CREDENTIALS", required=True))
    )
    sh = gc.open_by_key(src_id)
    ws = pick_tab(sh, env("SRC_TAB"))
    rows = ws.get_all_values()
    print(f"'{ws.title}' 에서 {len(rows)}행을 읽었다")

    hi, idx = find_header(rows)
    # 상태 칸은 있으면 쓰고 없으면 넘어간다. 판매가 멈춘 제품을 눌러 두는 데만 쓴다.
    머리 = [str(c).strip() for c in rows[hi]]
    상태칸 = 머리.index("Listing status") if "Listing status" in 머리 else None

    # 먼저 시트에 적힌 마지막 날짜를 찾는다. 수동 탭이라 오늘까지 차 있지 않다.
    날짜들 = [d for d in (to_date(r[0]) for r in rows[hi + 1:] if r) if d]
    if not 날짜들:
        sys.exit("날짜를 읽을 수 있는 행이 없다.")
    끝날 = max(날짜들)
    첫날 = 끝날 - datetime.timedelta(days=days - 1)
    print(f"집계 기간 {첫날} ~ {끝날} (시트 마지막 날짜 기준 {days}일)")

    합, 이름, 상태, 쓴행 = {}, {}, {}, 0
    for row in rows[hi + 1:]:
        if len(row) <= idx["creator"]:
            continue
        pid = str(row[idx["pid"]]).strip()
        if not PID.match(pid):
            continue
        d = to_date(row[0])
        if d is None or d < 첫날 or d > 끝날:
            continue
        합[pid] = 합.get(pid, 0.0) + to_num(row[idx["seller"]]) + to_num(
            row[idx["creator"]]
        )
        if not 이름.get(pid):
            이름[pid] = 이름다듬기(row[idx["name"]])
        if 상태칸 is not None and len(row) > 상태칸:
            # 같은 pid 가 여러 날 나온다. 마지막 날의 상태를 쓴다.
            상태[pid] = str(row[상태칸]).strip()
        쓴행 += 1

    팔린것 = {p: v for p, v in 합.items() if v > 0}
    print(f"집계에 쓴 행 {쓴행} · 기간 안에 라이브 매출이 있는 제품 {len(팔린것)}종")
    if not 팔린것:
        sys.exit("기간 안에 라이브 매출이 있는 제품이 없다.")

    순위 = [p for p, _ in sorted(팔린것.items(), key=lambda kv: -kv[1])][:n]

    # 이미 교안 쪽에 적어 둔 한국어 이름·슬러그·제품컷이 있으면 그대로 쓴다.
    옛제품 = {}
    try:
        옛제품 = json.load(open(TOP_JSON, encoding="utf-8")).get("제품", {})
    except OSError:
        pass
    slug표 = 슬러그표()

    제품 = collections.OrderedDict()
    새것 = []
    for pid in 순위:
        옛 = 옛제품.get(pid)
        if 옛:
            제품[pid] = collections.OrderedDict(옛)
            continue
        있는컷 = os.path.exists(os.path.join(IMG_DIR, f"{pid}.jpg"))
        제품[pid] = collections.OrderedDict([
            ("ko", 이름[pid]),      # 사람이 한국어로 고쳐 써야 한다
            ("en", 이름[pid]),
            ("slug", slug표.get(pid)),
            ("판매중", 상태.get(pid, "").lower() != "inactive"),
            ("이미지", f"/top/{pid}.jpg" if 있는컷 else None),
        ])
        새것.append(pid)

    out = collections.OrderedDict([
        ("_주", "라이브에서 많이 팔린 순서. 브랜드 자체 라이브(셀러)와 크리에이터 "
                "라이브를 더한 값으로 세웠다. 원본은 사내 '제품별 유입매출 RAW' 탭이다."),
        ("_기준", f"{SELLER_COL} + {CREATOR_COL} 합산 내림차순. {첫날} ~ {끝날}."),
        ("_왜시트", "CRUVA 의 제품별 live_gmv 는 크리에이터 라이브만 센다. 브랜드 "
                  "라이브가 제품별로 적힌 곳은 이 시트뿐이다."),
        ("_매출액없음", "순위만 싣고 금액은 싣지 않는다. 이 저장소는 공개다."),
        ("_밀림", "수동 탭이라 시트가 며칠 밀릴 수 있다. 그래서 오늘이 아니라 시트에 "
                "적힌 마지막 날짜를 끝으로 잡는다. 화면에도 그 날짜를 적는다."),
        ("집계끝", 끝날.isoformat()),
        ("기간ko", f"최근 {days}일 · {끝날} 집계분"),
        ("기간en", f"Last {days} days · through {끝날}"),
        ("순위", 순위),
        ("제품", 제품),
    ])

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print(f"순위 {len(순위)}개 → web/data/live-ranks.json")
    for i, pid in enumerate(순위, 1):
        print(f"  {i:>2}. {pid}  {제품[pid]['ko'][:54]}")
    if 새것:
        print(f"\n!! 교안 쪽에 없던 제품 {len(새것)}개. 한국어 이름을 손으로 "
              f"고쳐 쓰면 좋다: {', '.join(새것)}")
    빈컷 = [p for p in 순위 if not 제품[p]["이미지"]]
    if 빈컷:
        print(f"제품컷이 없는 제품 {len(빈컷)}개 — product-edu/shop_images.py "
              f"{' '.join(빈컷)} 로 받는다.")


if __name__ == "__main__":
    main()
