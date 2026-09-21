"""틱톡샵 제품별 라이브 유입매출을 pid 단위로 합산한다.

'매출지표 (슬랙, 주간보고)' 시트의 제품별 유입매출 RAW 탭을 읽어
제품(pid)마다 셀러 라이브와 크리에이터 라이브 매출을 더하고,
그 결과만 담은 작은 스프레드시트를 따로 만든다.

왜 따로 만드나:
  원본 시트가 4MB를 넘어 Drive 커넥터가 통째로 내보내지 못한다.
  결과만 담은 작은 시트를 만들어 두면 그건 바로 읽힌다.

왜 로그에 숫자를 안 찍나:
  이 저장소는 공개라 Actions 로그를 누구나 읽는다.
  매출은 시트에만 쓰고, 로그에는 몇 행을 읽었는지만 남긴다.

읽는 열 (원본 탭 기준):
  A 날짜 · B 제품명 · C pid
  G Seller LIVE-attributed GMV      ← 셀러 라이브 (직접+간접)
  N Creator LIVE-attributed GMV     ← 크리에이터 라이브 (직접+간접)
  H·O 는 간접을 뺀 직접 매출이라 쓰지 않는다. 탭 이름이 '유입매출'이므로
  attributed 쪽이 맞다.

환경변수:
  GOOGLE_CREDENTIALS  서비스 계정 JSON (필수)
  SRC_SHEET_ID        원본 스프레드시트 ID (필수)
  SRC_TAB             원본 탭 이름. 없으면 '유입매출' 이 든 탭을 찾는다
  DEST_SHEET_ID       결과 시트를 정해진 곳에 쓰고 싶을 때
  DEST_TITLE          결과 시트 제목 (기본: 'TikTok 라이브 유입매출 집계')
  SHARE_EMAIL         결과 시트를 공유할 주소
  DATE_FROM/DATE_TO   YYYY-MM-DD. 없으면 전체 기간
  TOP_N               결과에 실을 제품 수 (기본 50)
"""

import datetime
import json
import os
import re
import sys

import gspread

SELLER_COL = "Seller LIVE-attributed GMV"
CREATOR_COL = "Creator LIVE-attributed GMV"
PID = re.compile(r"^\d{15,25}$")


def env(name, default=None, required=False):
    v = os.environ.get(name, "").strip() or default
    if required and not v:
        sys.exit(f"{name} 이(가) 비어 있습니다.")
    return v


def to_num(v):
    """'1,234.5' · '$12' · '' 를 실수로. 숫자가 아니면 0."""
    if v is None:
        return 0.0
    s = str(v).strip().replace(",", "").replace("$", "").replace("%", "")
    if not s or s in ("-", "#N/A", "#VALUE!", "#REF!"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def to_date(v):
    """'2026. 1. 2' · '2026-01-02' · '1/2/2026' 를 date 로. 못 읽으면 None."""
    s = str(v or "").strip()
    if not s:
        return None
    s = re.sub(r"\s+", "", s).rstrip(".")
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def pick_tab(sh, want):
    """이름이 정확히 맞는 탭을 먼저, 없으면 '유입매출' 이 든 탭을 고른다."""
    titles = [ws.title for ws in sh.worksheets()]
    print(f"탭 {len(titles)}개: " + " | ".join(titles))
    if want:
        for t in titles:
            if t == want:
                return sh.worksheet(t)
        # 시트 제목은 공백·괄호가 쉽게 어긋난다. 느슨하게 한 번 더 본다.
        key = re.sub(r"\s", "", want)
        for t in titles:
            if re.sub(r"\s", "", t) == key:
                print(f"'{want}' 과(와) 공백만 다른 탭 '{t}' 을 쓴다")
                return sh.worksheet(t)
    hits = [t for t in titles if "유입매출" in t]
    if len(hits) == 1:
        print(f"이름이 안 맞아 '유입매출' 이 든 탭 '{hits[0]}' 을 쓴다")
        return sh.worksheet(hits[0])
    sys.exit(f"탭을 못 찾았다. 찾던 이름: {want!r}, '유입매출' 후보: {hits}")


def find_header(rows):
    """헤더 줄과 열 위치를 찾는다. 열이 밀려 있어도 이름으로 잡는다."""
    for i, row in enumerate(rows[:30]):
        cells = [str(c).strip() for c in row]
        if SELLER_COL in cells and CREATOR_COL in cells:
            idx = {
                "name": cells.index("Product Name"),
                "pid": cells.index("Product ID"),
                "seller": cells.index(SELLER_COL),
                "creator": cells.index(CREATOR_COL),
            }
            print(f"헤더는 {i+1}행. 열 위치(0부터): {idx}")
            expect = {"name": 1, "pid": 2, "seller": 6, "creator": 13}
            if idx != expect:
                print(f"!! 열 위치가 예상(B·C·G·N = {expect})과 다르다. 이름 기준으로 읽는다.")
            return i, idx
    sys.exit(f"'{SELLER_COL}' 과 '{CREATOR_COL}' 이 함께 있는 헤더 줄을 못 찾았다.")


def main():
    src_id = env("SRC_SHEET_ID", required=True)
    gc = gspread.service_account_from_dict(json.loads(env("GOOGLE_CREDENTIALS", required=True)))
    sh = gc.open_by_key(src_id)
    print(f"원본 시트: {sh.title}")

    ws = pick_tab(sh, env("SRC_TAB"))
    rows = ws.get_all_values()
    print(f"'{ws.title}' 에서 {len(rows)}행을 읽었다")

    hi, idx = find_header(rows)
    d_from = to_date(env("DATE_FROM"))
    d_to = to_date(env("DATE_TO"))
    if d_from or d_to:
        print(f"기간 제한: {d_from or '처음'} ~ {d_to or '끝'}")

    agg = {}
    쓴행 = 날짜밖 = 날짜없음 = pid이상 = 0
    최소 = 최대 = None
    for row in rows[hi + 1:]:
        if len(row) <= idx["creator"]:
            continue
        pid = str(row[idx["pid"]]).strip()
        if not pid:
            continue
        if not PID.match(pid):
            pid이상 += 1
            continue
        d = to_date(row[0])
        if d is None:
            날짜없음 += 1
        else:
            if (d_from and d < d_from) or (d_to and d > d_to):
                날짜밖 += 1
                continue
            최소 = d if 최소 is None or d < 최소 else 최소
            최대 = d if 최대 is None or d > 최대 else 최대
        a = agg.setdefault(pid, {"name": "", "seller": 0.0, "creator": 0.0, "n": 0})
        a["seller"] += to_num(row[idx["seller"]])
        a["creator"] += to_num(row[idx["creator"]])
        a["n"] += 1
        if not a["name"]:
            a["name"] = str(row[idx["name"]]).strip()
        쓴행 += 1

    print(f"집계에 쓴 행 {쓴행} · 기간 밖 {날짜밖} · 날짜 못 읽음 {날짜없음} · pid 아닌 행 {pid이상}")
    print(f"제품 {len(agg)}종, 실제 기간 {최소} ~ {최대}")
    if not agg:
        sys.exit("집계할 행이 없다.")

    순위 = sorted(agg.items(), key=lambda kv: -(kv[1]["seller"] + kv[1]["creator"]))
    top = 순위[: int(env("TOP_N", "50"))]

    머리 = ["순위", "pid", "제품명", "셀러 라이브 GMV", "크리에이터 라이브 GMV",
            "합산 GMV", "셀러 비중", "행 수"]
    표 = [머리]
    for i, (pid, a) in enumerate(top, 1):
        합 = a["seller"] + a["creator"]
        표.append([i, pid, a["name"], round(a["seller"], 2), round(a["creator"], 2),
                   round(합, 2), (round(a["seller"] / 합, 4) if 합 else ""), a["n"]])
    전체s = sum(a["seller"] for _, a in 순위)
    전체c = sum(a["creator"] for _, a in 순위)
    표 += [[], ["전체 합계", "", "", round(전체s, 2), round(전체c, 2),
                round(전체s + 전체c, 2), "", 쓴행]]

    meta = [
        ["원본 시트", sh.title],
        ["원본 탭", ws.title],
        ["집계 기간", f"{최소} ~ {최대}"],
        ["요청 기간", f"{d_from or '전체'} ~ {d_to or '전체'}"],
        ["셀러 라이브 열", SELLER_COL],
        ["크리에이터 라이브 열", CREATOR_COL],
        ["제품 수", len(agg)],
        ["집계에 쓴 행", 쓴행],
        ["pid 가 아니라 건너뛴 행", pid이상],
        ["만든 시각(UTC)", datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")],
    ]

    dest_id = env("DEST_SHEET_ID")
    title = env("DEST_TITLE", "TikTok 라이브 유입매출 집계")
    if dest_id:
        dest = gc.open_by_key(dest_id)
    else:
        try:
            dest = gc.open(title)
            print("같은 제목의 결과 시트가 있어 덮어쓴다")
        except gspread.SpreadsheetNotFound:
            dest = gc.create(title)
            print("결과 시트를 새로 만들었다")

    def put(name, values, rows_n, cols_n):
        try:
            w = dest.worksheet(name)
            w.clear()
        except gspread.WorksheetNotFound:
            w = dest.add_worksheet(title=name, rows=rows_n, cols=cols_n)
        w.update(values, "A1")
        return w

    put("집계", 표, len(표) + 10, len(머리) + 2)
    put("기준", meta, len(meta) + 5, 3)
    # 새로 만든 시트에 딸려 오는 빈 기본 탭은 치운다.
    for w in dest.worksheets():
        if w.title in ("Sheet1", "시트1") and w.row_count and not w.get_all_values():
            dest.del_worksheet(w)

    share = env("SHARE_EMAIL")
    if share:
        dest.share(share, perm_type="user", role="writer", notify=False)
        print(f"결과 시트를 {share} 에 공유했다")

    # 주소는 비밀이 아니다. 열려면 공유 권한이 있어야 한다. 매출 숫자는 안 찍는다.
    print(f"결과 시트: {dest.url}")
    print(f"상위 {len(top)}개와 전체 합계를 '집계' 탭에 썼다. 숫자는 로그에 남기지 않는다.")


if __name__ == "__main__":
    main()
