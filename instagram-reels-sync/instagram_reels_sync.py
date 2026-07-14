"""
인스타그램 릴스 아웃라이어 수집기 (Apify → 구글 시트)

구글 시트 "시트1" 탭 A열에 적힌 인스타그램 핸들 목록을 읽어,
Apify 의 instagram-scraper 액터로 각 계정의 최근 게시물을 가져온 뒤
릴스(Reels)만 골라 "최근 N일 평균 조회수 대비 배수"를 계산한다.

  - 배수(ratio) = 릴스 조회수 / 해당 계정의 최근 N일 릴스 평균 조회수
  - 배수가 큰 릴스 = 평소보다 잘 나온 영상(아웃라이어)

결과는 같은 스프레드시트의 두 탭에 저장한다.
  1) 릴스분석  : 릴스 단위 상세 (조회수/평균/배수/좋아요/댓글/게시일/캡션)
  2) 릴스요약  : 계정 단위 요약 (릴스수/평균/최고 조회수/최고 릴스)

환경변수(GitHub Actions Secrets/Variables 로 주입):
  APIFY_TOKEN         : Apify API 토큰            (필수)
  GOOGLE_CREDENTIALS  : 구글 서비스계정 JSON 문자열 (필수)
  SHEET_ID            : 대상 스프레드시트 ID       (선택, 기본값은 아래 DEFAULT_SHEET_ID)
  INPUT_TAB           : 핸들이 들어있는 탭 이름     (선택, 기본 "시트1")
  OUTPUT_TAB          : 릴스 상세 탭 이름          (선택, 기본 "릴스분석")
  SUMMARY_TAB         : 계정 요약 탭 이름          (선택, 기본 "릴스요약")
  DAYS                : 최근 며칠을 볼지           (선택, 기본 30)
  RESULTS_LIMIT       : 계정당 최대 수집 게시물 수  (선택, 기본 100)
  OUTPERFORM_RATIO    : 아웃라이어로 표시할 배수 기준(선택, 기본 2.0)
  APIFY_ACTOR         : 사용할 액터 ID            (선택, 기본 "apify/instagram-scraper")
"""

import json
import os
from datetime import datetime, timedelta, timezone

import gspread
from apify_client import ApifyClient

# 사용자가 지정한 대상 스프레드시트 (필요 시 SHEET_ID 로 덮어쓸 수 있음)
DEFAULT_SHEET_ID = "1GBbJLkwbKOjG0xKoBaICB9505ueLWuDIMMAPCyvoUU4"
DEFAULT_ACTOR = "apify/instagram-scraper"


def _env(name, default=None):
    """환경변수를 읽되 비어 있으면(빈 문자열 포함) default 를 돌려준다."""
    value = os.environ.get(name)
    return value if value else default


def _int_env(name, default):
    try:
        return int(_env(name, default))
    except (TypeError, ValueError):
        return default


def _float_env(name, default):
    try:
        return float(_env(name, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# 구글 시트
# ---------------------------------------------------------------------------
def build_gspread_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError(
            "GOOGLE_CREDENTIALS 환경변수가 비어 있습니다. "
            "구글 서비스계정 JSON 을 Secret 으로 주입하세요."
        )
    creds_dict = json.loads(creds_json)
    return gspread.service_account_from_dict(creds_dict)


def read_handles(sh, tab_name):
    """지정한 탭 A열에서 핸들 목록을 읽는다. 헤더/빈칸/@ 는 정리한다."""
    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        raise RuntimeError(f"입력 탭 '{tab_name}' 을(를) 찾지 못했습니다.")

    col = ws.col_values(1)
    handles = []
    seen = set()
    for raw in col:
        handle = (raw or "").strip().lstrip("@")
        if not handle:
            continue
        # 헤더로 보이는 값은 건너뜀
        if handle.lower() in {"instagram handle", "handle", "핸들", "instagram"}:
            continue
        # URL 형태로 들어온 경우 마지막 경로만 취함
        if "instagram.com/" in handle:
            handle = handle.rstrip("/").split("/")[-1]
        key = handle.lower()
        if key in seen:
            continue
        seen.add(key)
        handles.append(handle)
    return handles


def get_or_create_worksheet(sh, title, header):
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=max(12, len(header)))
    return ws


def overwrite_worksheet(sh, title, header, rows):
    ws = get_or_create_worksheet(sh, title, header)
    ws.clear()
    ws.update("A1", [header] + rows, value_input_option="USER_ENTERED")


# ---------------------------------------------------------------------------
# Apify
# ---------------------------------------------------------------------------
def fetch_posts(handles, days, results_limit, actor_id):
    """모든 핸들을 한 번의 액터 run 으로 수집해 게시물 아이템 리스트를 반환."""
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise ValueError(
            "APIFY_TOKEN 환경변수가 비어 있습니다. Apify API 토큰을 Secret 으로 주입하세요."
        )

    client = ApifyClient(token)
    urls = [f"https://www.instagram.com/{h}/" for h in handles]
    run_input = {
        "directUrls": urls,
        "resultsType": "posts",
        "resultsLimit": results_limit,
        "onlyPostsNewerThan": f"{days} days",
        "addParentData": False,
    }

    print(f"🚀 Apify 액터 실행: {actor_id} / 계정 {len(urls)}개 / 최근 {days}일")
    run = client.actor(actor_id).call(run_input=run_input)
    dataset_id = _run_dataset_id(run)
    if not dataset_id:
        raise RuntimeError(f"Apify run 에서 데이터셋 ID 를 찾지 못했습니다: {run!r}")
    items = list(client.dataset(dataset_id).iterate_items())
    print(f"   데이터셋 아이템 {len(items)}개 수신")
    return items


def _run_dataset_id(run):
    """apify-client 버전에 따라 run 이 dict 또는 Run 객체로 반환된다.
    두 경우 모두에서 defaultDatasetId 를 안전하게 꺼낸다."""
    if isinstance(run, dict):
        return run.get("defaultDatasetId") or run.get("default_dataset_id")
    # apify-client >= 2.0 은 타입 객체를 반환 (속성 접근)
    for attr in ("default_dataset_id", "defaultDatasetId"):
        val = getattr(run, attr, None)
        if val:
            return val
    # Pydantic 모델 폴백
    for dumper in ("model_dump", "dict"):
        fn = getattr(run, dumper, None)
        if callable(fn):
            try:
                data = fn()
            except TypeError:
                continue
            if isinstance(data, dict):
                return data.get("defaultDatasetId") or data.get("default_dataset_id")
    return None


# ---------------------------------------------------------------------------
# 데이터 가공
# ---------------------------------------------------------------------------
def is_reel(item):
    """릴스 여부 판별. productType == 'clips' 가 가장 확실하며,
    없으면 동영상 타입으로 폴백한다."""
    if item.get("productType") == "clips":
        return True
    return item.get("type") == "Video"


def get_views(item):
    """릴스 조회수. 액터/버전에 따라 필드명이 달라 여러 후보를 시도한다."""
    for key in (
        "videoPlayCount",
        "videoViewCount",
        "playCount",
        "viewsCount",
        "videoViews",
    ):
        val = item.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return int(val)
    return 0


def parse_timestamp(item):
    ts = item.get("timestamp")
    if not ts:
        return None
    try:
        # 예: "2024-05-01T12:34:56.000Z"
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def short_caption(item, limit=80):
    cap = (item.get("caption") or "").replace("\n", " ").strip()
    return cap[:limit] + ("…" if len(cap) > limit else "")


def owner_of(item):
    return (item.get("ownerUsername") or "").strip().lower()


def build_reels_by_handle(handles, items, days):
    """핸들(소문자) → 릴스 리스트 로 그룹핑. 최근 N일 이내 릴스만 남긴다."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    reels_by_handle = {h.lower(): [] for h in handles}

    for item in items:
        if item.get("error"):
            continue
        if not is_reel(item):
            continue
        owner = owner_of(item)
        if owner not in reels_by_handle:
            continue
        ts = parse_timestamp(item)
        if ts is not None and ts < cutoff:
            continue
        views = get_views(item)
        reels_by_handle[owner].append(
            {
                "url": item.get("url") or f"https://www.instagram.com/reel/{item.get('shortCode', '')}/",
                "views": views,
                "likes": item.get("likesCount") or 0,
                "comments": item.get("commentsCount") or 0,
                "timestamp": ts,
                "caption": short_caption(item),
            }
        )
    return reels_by_handle


def analyze(handles, reels_by_handle, outperform_ratio):
    """릴스 상세 행과 계정 요약 행을 만든다."""
    detail_rows = []
    summary_rows = []

    for original_handle in handles:
        key = original_handle.lower()
        reels = reels_by_handle.get(key, [])
        counted = [r for r in reels if r["views"] > 0]

        if not reels:
            summary_rows.append(
                [original_handle, 0, "", "", "", "데이터 없음(비공개/미존재/최근 릴스 없음)"]
            )
            continue

        avg = round(sum(r["views"] for r in counted) / len(counted)) if counted else 0
        best = max(reels, key=lambda r: r["views"])

        summary_rows.append(
            [
                original_handle,
                len(reels),
                avg,
                best["views"],
                best["url"],
                "정상",
            ]
        )

        # 배수 계산 후 배수 내림차순 정렬
        for r in reels:
            ratio = round(r["views"] / avg, 2) if avg > 0 else ""
            r["ratio"] = ratio
        reels_sorted = sorted(
            reels, key=lambda r: (r["ratio"] if isinstance(r["ratio"], (int, float)) else -1),
            reverse=True,
        )

        for r in reels_sorted:
            is_outlier = isinstance(r["ratio"], (int, float)) and r["ratio"] >= outperform_ratio
            detail_rows.append(
                [
                    original_handle,
                    r["url"],
                    r["views"],
                    avg,
                    r["ratio"],
                    "★" if is_outlier else "",
                    r["likes"],
                    r["comments"],
                    r["timestamp"].strftime("%Y-%m-%d") if r["timestamp"] else "",
                    r["caption"],
                ]
            )

    return detail_rows, summary_rows


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main():
    sheet_id = _env("SHEET_ID", DEFAULT_SHEET_ID)
    input_tab = _env("INPUT_TAB", "시트1")
    output_tab = _env("OUTPUT_TAB", "릴스분석")
    summary_tab = _env("SUMMARY_TAB", "릴스요약")
    days = _int_env("DAYS", 30)
    results_limit = _int_env("RESULTS_LIMIT", 100)
    outperform_ratio = _float_env("OUTPERFORM_RATIO", 2.0)
    actor_id = _env("APIFY_ACTOR", DEFAULT_ACTOR)

    print("🔐 구글 시트 인증 중...")
    gc = build_gspread_client()
    sh = gc.open_by_key(sheet_id)
    print(f"   📄 시트: {sh.title} / {sh.url}")

    handles = read_handles(sh, input_tab)
    if not handles:
        raise RuntimeError(f"'{input_tab}' 탭 A열에서 핸들을 찾지 못했습니다.")
    print(f"👤 핸들 {len(handles)}개 로드")

    items = fetch_posts(handles, days, results_limit, actor_id)
    reels_by_handle = build_reels_by_handle(handles, items, days)

    total_reels = sum(len(v) for v in reels_by_handle.values())
    print(f"🎬 최근 {days}일 릴스 총 {total_reels}개 확인")

    detail_rows, summary_rows = analyze(handles, reels_by_handle, outperform_ratio)

    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    detail_header = [
        f"handle (업데이트 {stamp})",
        "릴스URL",
        "조회수",
        f"{days}일평균조회수",
        "배수",
        f"우수(≥{outperform_ratio}x)",
        "좋아요",
        "댓글",
        "게시일",
        "캡션",
    ]
    summary_header = [
        f"handle (업데이트 {stamp})",
        f"릴스수({days}일)",
        "평균조회수",
        "최고조회수",
        "최고릴스URL",
        "상태",
    ]

    print(f"📊 '{summary_tab}' 저장 중...")
    overwrite_worksheet(sh, summary_tab, summary_header, summary_rows)
    print(f"📊 '{output_tab}' 저장 중... (릴스 {len(detail_rows)}행)")
    overwrite_worksheet(sh, output_tab, detail_header, detail_rows)

    outliers = sum(1 for row in detail_rows if row[5] == "★")
    print(f"🎉 완료! 아웃라이어(≥{outperform_ratio}x) {outliers}개")
    print(f"👉 {sh.url}")


if __name__ == "__main__":
    main()
