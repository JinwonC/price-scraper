"""브랜드 라이브 일정 시트 → web/data/live-schedule.json

크리에이터가 브랜드 라이브와 시간이 겹치지 않게 방송을 잡으려면 일정을
먼저 봐야 한다. 그래서 사이트에 '브랜드 라이브 일정' 화면을 두고, 그 화면이
읽는 파일을 이 스크립트가 만든다.

시트는 커넥터(MCP)로 읽는다. 스크립트가 바로 부를 수 없어서, 받은 값을
JSON 으로 떨어뜨려 두고 이 스크립트에 넘긴다. 받는 법은 README 에 적었다.

읽는 칸 (Schedule 탭)
  A 날짜 · B 계정 · C 시작 · D 종료 · E 예정 시간
  F(GMV 계획)는 읽지 않는다 — 매출 목표라 싣지 않는다. 이 저장소는 공개다.

시간
  시작·종료 칸에는 '2026/11/05 12:00 (EDT)' 처럼 꼬리표가 붙어 있는데,
  11월 1일부터는 동부가 EST 라 꼬리표가 실제와 맞지 않는다. 그래서 꼬리표는
  읽지 않고, 적힌 시각을 뉴욕 현지 시각으로 보고 그 날짜의 미국 동부
  규칙으로 UTC 로 바꾼다. 화면에서 다른 시간대로 보여 줄 때도 이 UTC 를
  기준으로 각 시간대의 서머타임 규칙을 따라 다시 적는다.

지난 일정은 싣지 않는다. 피해서 잡는 데 쓰는 화면이라 오늘부터가 쓸모다.

사용: python schedule.py <시트값.json> [--today 2026-10-21]
"""

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "web", "data", "live-schedule.json")
ET = ZoneInfo("America/New_York")

# '2026/11/05 12:00 (EDT)' · '2026-11-05 12:00' · '11/5/2026 12:00 PM' 모두 받는다.
시각꼴 = re.compile(
    r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})\s*(AM|PM)?",
    re.I,
)
# 계정 칸 표기가 들쑥날쑥하다('latam', 'LATAM', 'Global'). 화면에 쓸 이름으로 맞춘다.
계정이름 = {
    "global": ("글로벌", "Global"),
    "latam": ("라탐", "LATAM"),
    "us": ("US", "US"),
}


def 시각(값):
    """시트 칸 → 뉴욕 현지 시각. 못 읽으면 None."""
    m = 시각꼴.search(str(값 or ""))
    if not m:
        return None
    y, mo, d, h, mi, ampm = m.groups()
    h = int(h)
    if ampm:
        ampm = ampm.upper()
        if ampm == "PM" and h != 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
    return dt.datetime(int(y), int(mo), int(d), h, int(mi), tzinfo=ET)


def 날짜밀기(t, 차):
    """날짜만 옮긴다. 벽시계 시각은 그대로 두려고 날짜를 바꿔 다시 만든다
    (서머타임 경계를 넘을 때 timedelta 를 더하면 한 시간이 밀린다)."""
    return dt.datetime.combine(t.date() + 차, t.timetz()).replace(tzinfo=ET)


def utc(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json", help="커넥터로 받은 Schedule 탭 값 (JSON)")
    ap.add_argument("--today", help="기준 날짜. 없으면 동부 기준 오늘")
    a = ap.parse_args()

    raw = json.load(open(a.json, encoding="utf-8"))
    rows = raw["values"] if isinstance(raw, dict) else raw
    if not rows:
        sys.exit("시트 값이 비어 있다.")

    오늘 = (
        dt.date.fromisoformat(a.today)
        if a.today
        else dt.datetime.now(ET).date()
    )
    자정 = dt.datetime.combine(오늘, dt.time(0, 0), tzinfo=ET)

    일정, 못읽음, 지난것, 어긋남 = [], 0, 0, []
    for r in rows[1:]:
        칸 = (list(r) + [""] * 5)[:5]
        계정, 시작, 끝 = 칸[1], 시각(칸[2]), 시각(칸[3])
        if not 시작:
            못읽음 += 1
            continue
        # 날짜 칸과 시작 칸의 날짜가 어긋난 줄이 있다(시트에서 한 주를 안 밀고
        # 복사한 자리). 날짜 칸을 믿고 시각만 옮겨 쓰되, 사람이 볼 수 있게
        # '확인 필요' 로 표시하고 아래에 찍어 준다.
        날짜 = 시각(str(칸[0]) + " 00:00")
        틀림 = bool(날짜 and 날짜.date() != 시작.date())
        if 틀림:
            차 = 날짜.date() - 시작.date()
            어긋남.append(f"{칸[0]} {계정} — 시작 칸은 {시작.date()}")
            시작 = 날짜밀기(시작, 차)
            끝 = 날짜밀기(끝, 차) if 끝 else 끝
        # 종료가 비었거나 시작보다 이르면(자정을 넘긴 표기) 예정 시간으로 메운다.
        if not 끝 or 끝 <= 시작:
            try:
                끝 = 시작 + dt.timedelta(hours=float(칸[4]))
            except (TypeError, ValueError):
                끝 = None
        if 끝 and 끝 < 자정:
            지난것 += 1
            continue
        키 = str(계정).strip().lower()
        ko, en = 계정이름.get(키, (str(계정).strip(), str(계정).strip()))
        줄 = collections.OrderedDict([
            ("계정ko", ko),
            ("계정en", en),
            ("시작", utc(시작)),
            ("끝", utc(끝) if 끝 else None),
        ])
        if 틀림:
            줄["확인필요"] = True
        일정.append(줄)

    일정.sort(key=lambda x: (x["시작"], x["계정en"]))
    out = collections.OrderedDict([
        ("_주", "d'Alba 브랜드 자체 라이브 일정. 크리에이터가 겹치지 않게 "
                "방송을 잡는 데 쓴다. 원본은 사내 'Schedule' 시트다."),
        ("_시간대", "시각은 UTC 로 적어 둔다. 원본 시트는 미국 동부 현지 시각으로 "
                  "적혀 있고(꼬리표가 11월에도 EDT 로 남아 있어 꼬리표는 읽지 "
                  "않는다), 화면에서 보는 사람의 시간대로 다시 적는다."),
        ("_금액없음", "시트의 GMV 계획 칸은 싣지 않는다. 이 저장소는 공개다."),
        ("_지난것", "지난 일정은 담지 않는다. 기준 날짜 0시(동부) 이후만 남긴다."),
        ("_확인필요", "시트의 날짜 칸과 시작·종료 칸의 날짜가 어긋난 줄이다. "
                    "날짜 칸을 믿고 시각만 옮겨 적었고, 화면에도 표시해 둔다."),
        ("기준", 오늘.isoformat()),
        ("일정", 일정),
    ])

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")

    계정수 = collections.Counter(x["계정en"] for x in 일정)
    print(f"일정 {len(일정)}개 → {os.path.relpath(OUT, HERE)}  ({dict(계정수)})")
    if 일정:
        print(f"  {일정[0]['시작']} ~ {일정[-1]['시작']} (UTC)")
    if 지난것:
        print(f"  지난 일정 {지난것}개는 빼 두었다.")
    if 못읽음:
        print(f"  !! 시작 시각을 못 읽은 줄 {못읽음}개. 시트 표기를 봐야 한다.")
    if 어긋남:
        print(f"  !! 날짜 칸과 시각 칸이 어긋난 줄 {len(어긋남)}개 "
              f"— 날짜 칸대로 옮겨 적고 '확인 필요' 로 표시했다:")
        for 줄 in 어긋남:
            print(f"     {줄}")


if __name__ == "__main__":
    main()
