"""BFCM 딜 가격표를 만든다. 시트 두 탭 → web/data/deal-prices.json.

받는 것:
  <sku.tsv>   'Deal Price' 탭. pid · SKU 이름 · 정가 · 딜가 · 할인율(%)
  <live.tsv>  'PID별 7일 매출' 탭. pid · LIVE GMV. 차례를 정하는 데만 쓴다.

**금액은 가격만 싣는다.** LIVE GMV 는 순서를 매기는 데 쓰고 파일에는 쓰지
않는다 — 이 저장소는 공개다. 샵에 걸린 정가·딜가·할인율은 누구나 보는
값이라 그대로 싣는다.

이름은 deal-price/names.json 에서 가져온다. 시트의 리스팅 이름은 길어서
카드에 넣으면 읽히지 않는다. 처음 보는 pid 는 이름이 없다고 알려 준다.

사용:
  python deal.py <sku.tsv> <live.tsv> [--today YYYY-MM-DD]
"""

import argparse
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")
NAMES = os.path.join(HERE, "names.json")
OUT = os.path.join(WEB, "data", "deal-prices.json")
IMG_DIR = os.path.join(WEB, "public", "deal")
TOP_DIR = os.path.join(WEB, "public", "top")


def 줄들(path):
    with open(path, encoding="utf-8") as f:
        for 줄 in f:
            줄 = 줄.rstrip("\n")
            if 줄.strip():
                yield 줄.split("\t")


def 돈(s):
    return float(s.replace("$", "").replace(",", "").strip())


def 이미지(pid):
    """제품컷. 상위 10개용으로 받아 둔 것이 있으면 그걸 쓴다."""
    for 경로, 주소 in ((TOP_DIR, "/top"), (IMG_DIR, "/deal")):
        if os.path.exists(os.path.join(경로, f"{pid}.jpg")):
            return f"{주소}/{pid}.jpg"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sku")
    ap.add_argument("live")
    ap.add_argument("--today", help="기준 날짜. 없으면 오늘(UTC)")
    a = ap.parse_args()

    이름표 = json.load(open(NAMES, encoding="utf-8"))["제품"]
    라이브 = {pid: 돈(gmv) for pid, gmv in 줄들(a.live)}

    상품 = {}
    for pid, sku, 정가, 딜가, 할인 in 줄들(a.sku):
        it = 상품.setdefault(pid, {"pid": pid, "sku": []})
        it["sku"].append({
            "이름": sku.strip(),
            "정가": 돈(정가),
            "딜가": 돈(딜가),
            "할인": round(float(할인.replace("%", "")), 1),
        })

    모르는 = [p for p in 상품 if p not in 이름표]
    for pid, it in 상품.items():
        n = 이름표.get(pid, {})
        it["ko"] = n.get("ko", "")
        it["en"] = n.get("en", "")
        it["태그"] = n.get("태그", "할인")
        it["이미지"] = 이미지(pid)
        # SKU 는 할인이 큰 것부터. 방송에서 먼저 불러 주는 값이 위로 온다.
        it["sku"].sort(key=lambda s: -s["할인"])

    # 제품 차례는 라이브 매출이 큰 순. 시트에 없는 pid 는 뒤로 보낸다.
    줄선것 = sorted(상품.values(), key=lambda it: -라이브.get(it["pid"], -1.0))

    할인들 = [s["할인"] for it in 줄선것 for s in it["sku"]]
    data = {
        "_주": "US 틱톡샵 BFCM 딜 가격표. 정가·딜가·할인율은 샵에 걸린 값 그대로다.",
        "_차례": "제품은 최근 7일 라이브 매출이 큰 순이다. 매출액은 싣지 않는다 — 이 저장소는 공개다.",
        "_시트": "https://docs.google.com/spreadsheets/d/1p9HmIOGnc5gE8kQILFT3T_8NAuKMRc-RkY2cs_gQu0M — 'Deal Price' 탭과 'PID별 7일 매출' 탭.",
        "_이름": "짧은 이름은 deal-price/names.json 에 적어 둔 것이다. 리스팅 이름 그대로는 카드에 들어가지 않는다.",
        "기준": a.today or datetime.date.today().isoformat(),
        # 화면에 '마지막 갱신' 으로 적는다. 가격은 하루에도 바뀌어서 날짜만으로는 모자라다.
        "갱신": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
        "요약": {
            "제품수": len(줄선것),
            "sku수": len(할인들),
            "평균할인": round(sum(할인들) / len(할인들), 1) if 할인들 else 0,
            "최대할인": max(할인들) if 할인들 else 0,
        },
        "상품": 줄선것,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    붙은것 = sum(1 for it in 줄선것 if it["이미지"])
    print(f"제품 {len(줄선것)} · SKU {len(할인들)} → web/data/deal-prices.json")
    print(f"  평균 할인 {data['요약']['평균할인']}% · 최대 {data['요약']['최대할인']}%")
    print(f"  제품컷 {붙은것}/{len(줄선것)}")
    if 모르는:
        print(f"\n!! 이름표가 없는 pid {len(모르는)}개. names.json 에 적어야 한다:")
        for p in 모르는:
            print(f"  - {p}")


if __name__ == "__main__":
    main()
