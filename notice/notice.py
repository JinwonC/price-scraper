"""공지 시트 → web/data/notice.json 의 '공지' 칸.

사이트는 공지를 두 길로 받는다.
  1) 화면이 열릴 때 시트를 csv 로 직접 읽는다 — 사장님이 시트에 쓰면 바로 뜬다.
     시트가 '링크가 있는 모든 사용자 · 뷰어' 여야 읽힌다.
  2) 그 길이 막혔을 때를 대비해, 매일 한 번 시트 내용을 저장소에 구워 둔다.
     이 스크립트가 그 일을 한다.

시트는 커넥터(MCP)로 읽는다. 받은 값을 JSON 으로 떨어뜨려 두고 넘긴다.

시트 칸
  표시(Y/N) · 제목 · 본문 · 링크 · 링크문구 · 시작일 · 종료일 · 비고
  '비고' 는 사람끼리 보는 칸이라 사이트로 내보내지 않는다.
  표시가 Y 가 아닌 줄은 빼고, 기간이 지난 줄도 빼 둔다(화면에서 한 번 더 거른다).

사용: python notice.py <시트값.json> [--today 2026-10-22]
"""

import argparse
import collections
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "web", "data", "notice.json")
칸들 = ["표시", "제목", "본문", "링크", "링크문구", "시작일", "종료일"]


def 날짜(s):
    s = str(s or "").strip().replace("/", "-").replace(". ", "-").rstrip(".")
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json", help="커넥터로 받은 '공지' 탭 값 (JSON)")
    ap.add_argument("--today", help="기준 날짜. 없으면 오늘(UTC)")
    a = ap.parse_args()

    raw = json.load(open(a.json, encoding="utf-8"))
    rows = raw["values"] if isinstance(raw, dict) else raw
    if not rows:
        sys.exit("시트 값이 비어 있다.")

    오늘 = datetime.date.fromisoformat(a.today) if a.today else datetime.date.today()
    머리 = [str(c).strip() for c in rows[0]]
    자리 = {k: (머리.index(k) if k in 머리 else -1) for k in 칸들}
    if 자리["제목"] < 0:
        sys.exit(f"'제목' 칸을 못 찾았다. 머리줄: {머리}")

    공지, 꺼둔것, 지난것 = [], 0, 0
    for r in rows[1:]:
        칸 = lambda k: ("" if 자리[k] < 0 or 자리[k] >= len(r) else str(r[자리[k]]).strip())
        if 칸("표시").upper() not in ("Y", "YES", "TRUE"):
            꺼둔것 += 1
            continue
        시작, 종료 = 날짜(칸("시작일")), 날짜(칸("종료일"))
        if (시작 and 오늘 < 시작) or (종료 and 오늘 > 종료):
            지난것 += 1
            continue
        if not 칸("제목") and not 칸("본문"):
            continue
        줄 = collections.OrderedDict([("제목", 칸("제목")), ("본문", 칸("본문"))])
        for k in ("링크", "링크문구", "시작일", "종료일"):
            if 칸(k):
                줄[k] = 칸(k)
        공지.append(줄)

    d = json.load(open(OUT, encoding="utf-8"), object_pairs_hook=collections.OrderedDict)
    d["공지"] = 공지
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print(f"공지 {len(공지)}개 → web/data/notice.json"
          f" (꺼 둔 줄 {꺼둔것}, 기간 밖 {지난것})")
    for 줄 in 공지:
        print(f"  - {줄['제목'][:50]}")


if __name__ == "__main__":
    main()
