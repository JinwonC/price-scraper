"""CRUVA 에서 받은 제품 성과 CSV 로 web/data/top10.json 을 다시 만든다.

CRUVA 는 MCP 도구라 스크립트가 바로 부를 수 없다. 그래서 사람이(또는 클로드가)
CSV 를 받아 두고 이 스크립트에 넘긴다. 받는 법은 README 에 적어 두었다.

하는 일:
  - total_gmv 로 1~10위, live_gmv 로 1~10위를 뽑는다
  - 이미 있던 제품의 한국어 이름·슬러그·이미지는 그대로 쓴다
  - 처음 보는 제품은 영어 이름만 채워 두고 "이름을 써 달라" 고 알린다
  - 어느 순위에도 안 드는 제품은 '제품' 표에서 치운다

매출액은 쓰지 않는다. 순위만 쓴다. 이 저장소는 공개다.

사용: python top_ranks.py <csv> --from 2026-09-10 --to 2026-10-10
"""

import argparse
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP_JSON = os.path.join(HERE, "..", "web", "data", "top10.json")
필요칸 = {"product_id", "product_name", "total_gmv", "live_gmv"}


def 수(r, k):
    try:
        return float(r.get(k) or 0)
    except ValueError:
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--from", dest="부터", required=True)
    ap.add_argument("--to", dest="까지", required=True)
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.csv, encoding="utf-8-sig")))
    if not rows:
        sys.exit("CSV 가 비어 있다.")
    빠진칸 = 필요칸 - set(rows[0])
    if 빠진칸:
        sys.exit(f"CSV 에 없는 칸: {', '.join(sorted(빠진칸))}")

    old = json.load(open(TOP_JSON, encoding="utf-8"),
                    object_pairs_hook=collections.OrderedDict)
    옛제품 = old.get("제품", {})

    전체 = [r["product_id"] for r in sorted(rows, key=lambda r: -수(r, "total_gmv"))[: a.n]]
    라이브 = [r["product_id"] for r in sorted(rows, key=lambda r: -수(r, "live_gmv"))[: a.n]]
    이름표 = {r["product_id"]: r for r in rows}

    제품, 새것 = collections.OrderedDict(), []
    for pid in 전체 + 라이브:
        if pid in 제품:
            continue
        if pid in 옛제품:
            제품[pid] = 옛제품[pid]
            continue
        r = 이름표[pid]
        # status 는 CSV 에 따라 'available' 로도 '1' 로도 온다. 둘 다 파는 중이다.
        팔림 = str(r.get("status", "")).strip().lower() in ("available", "1", "true", "")
        제품[pid] = collections.OrderedDict([
            ("ko", r["product_name"]),      # 사람이 한국어로 고쳐 써야 한다
            ("en", r["product_name"]),
            ("slug", None),
            ("판매중", 팔림),
            ("이미지", None),
        ])
        새것.append(pid)

    old["_기준"] = (f"'전체' 는 total_gmv, '크리에이터 라이브' 는 live_gmv 내림차순. "
                  f"둘 다 {a.부터} ~ {a.까지}.")
    old["기간ko"] = f"최근 30일 · {a.까지} 기준"
    old["기간en"] = f"Last 30 days · as of {a.까지}"
    old["전체"], old["라이브"], old["제품"] = 전체, 라이브, 제품

    with open(TOP_JSON, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=1)
        f.write("\n")

    사라짐 = [p for p in 옛제품 if p not in 제품]
    print(f"전체 {len(전체)} · 라이브 {len(라이브)} · 제품 {len(제품)}")
    if 사라짐:
        print(f"순위 밖으로 나가 치운 제품 {len(사라짐)}개:")
        for p in 사라짐:
            print(f"  - {옛제품[p]['ko'][:46]}")
    if 새것:
        print(f"\n!! 처음 보는 제품 {len(새것)}개. 한국어 이름과 슬러그를 손으로 채워야 한다:")
        for p in 새것:
            print(f"  - {p}  {제품[p]['en'][:66]}")
        print("   제품컷은 'python shop_images.py' 로 받는다.")
    else:
        print("새로 들어온 제품 없음.")
    빈이미지 = [p for p in 제품 if not 제품[p]["이미지"]]
    if 빈이미지:
        print(f"제품컷이 없는 제품 {len(빈이미지)}개 — shop_images.py 로 받는다.")


if __name__ == "__main__":
    main()
