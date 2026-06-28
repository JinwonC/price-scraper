"""
와썹맨 YouTube 스튜디오 -> 구글 스프레드시트 자동 수집기

하나의 OAuth 자격증명으로 아래 3가지를 모두 처리합니다.
  1) YouTube Data API v3       : 채널/영상 공개 통계 (구독자, 조회수, 좋아요 등)
  2) YouTube Analytics API     : 스튜디오 분석 지표 (시청시간, 노출수, CTR, 트래픽 소스 등)
  3) Google Sheets (gspread)   : 결과를 새 스프레드시트에 자동 생성/갱신

환경변수(GitHub Actions Secrets로 주입):
  GOOGLE_OAUTH_CLIENT_ID       : OAuth 클라이언트 ID
  GOOGLE_OAUTH_CLIENT_SECRET   : OAuth 클라이언트 시크릿
  GOOGLE_OAUTH_REFRESH_TOKEN   : get_refresh_token.py 로 발급받은 리프레시 토큰
  SHEET_TITLE (선택)           : 스프레드시트 제목 (기본: "와썹맨 YouTube 통계")
  SHEET_ID    (선택)           : 특정 스프레드시트에 고정하고 싶을 때 ID 지정
  SHARE_EMAIL (선택)           : 생성된 시트를 공유할 이메일 (편집 권한)
"""

import os
from datetime import date, timedelta

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# OAuth 하나로 YouTube + Analytics + Sheets/Drive 전부 커버
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DEFAULT_SHEET_TITLE = "와썹맨 YouTube 통계"


def _env(name, default=None):
    """환경변수를 읽되, 비어 있으면(빈 문자열 포함) default 를 돌려준다.
    GitHub Actions 에서 정의되지 않은 vars.* 는 빈 문자열로 주입되므로 필요."""
    value = os.environ.get(name)
    return value if value else default

# 최근 영상 중 최대 몇 개까지 영상별 통계를 수집할지
MAX_VIDEOS = 50
# 분석 지표를 며칠치까지 거슬러 올라가며 백필할지 (데이터 확정에 2~3일 지연이 있어 넉넉히)
ANALYTICS_LOOKBACK_DAYS = 10


# ---------------------------------------------------------------------------
# 인증
# ---------------------------------------------------------------------------
def build_credentials():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN")

    missing = [
        name
        for name, val in [
            ("GOOGLE_OAUTH_CLIENT_ID", client_id),
            ("GOOGLE_OAUTH_CLIENT_SECRET", client_secret),
            ("GOOGLE_OAUTH_REFRESH_TOKEN", refresh_token),
        ]
        if not val
    ]
    if missing:
        raise ValueError(
            "다음 환경변수가 비어 있습니다: "
            + ", ".join(missing)
            + "\n  README의 '셋업' 단계를 따라 OAuth 자격증명을 준비하세요."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    creds.refresh(Request())  # 액세스 토큰 발급
    return creds


# ---------------------------------------------------------------------------
# YouTube Data API : 공개 통계
# ---------------------------------------------------------------------------
def get_authorized_channel_id(youtube):
    """OAuth 토큰에 묶인(mine) 채널 ID. 분석 API 접근 가능 여부 판별에 사용."""
    resp = youtube.channels().list(part="id", mine=True).execute()
    items = resp.get("items", [])
    return items[0]["id"] if items else None


def resolve_target_channel_id(youtube):
    """수집 대상 채널 ID를 결정한다.
    우선순위: YOUTUBE_CHANNEL_ID > YOUTUBE_CHANNEL_HANDLE > None(=인증 채널 mine).
    공개 통계는 어떤 채널이든 채널 ID/핸들만 있으면 가져올 수 있다."""
    cid = _env("YOUTUBE_CHANNEL_ID")
    if cid:
        return cid
    handle = _env("YOUTUBE_CHANNEL_HANDLE")
    if handle:
        resp = youtube.channels().list(part="id", forHandle=handle).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["id"]
        print(f"  ⚠️ 핸들 '{handle}' 로 채널을 찾지 못했습니다. 인증 채널로 진행합니다.")
    return None


def fetch_channel_summary(youtube, channel_id=None):
    """채널 요약 통계와 업로드 재생목록 ID를 반환.
    channel_id 가 없으면 인증 채널(mine), 있으면 해당 채널의 공개 통계."""
    params = {"part": "snippet,statistics,contentDetails"}
    if channel_id:
        params["id"] = channel_id
    else:
        params["mine"] = True
    resp = youtube.channels().list(**params).execute()
    items = resp.get("items", [])
    if not items:
        raise RuntimeError("대상 YouTube 채널을 찾지 못했습니다.")
    ch = items[0]
    stats = ch.get("statistics", {})
    summary = {
        "channel_id": ch["id"],
        "title": ch["snippet"]["title"],
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "total_videos": int(stats.get("videoCount", 0)),
    }
    uploads_playlist = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    return summary, uploads_playlist


def fetch_recent_videos(youtube, uploads_playlist, limit=MAX_VIDEOS):
    """업로드 재생목록에서 최근 영상 ID를 모은 뒤 영상별 통계를 반환."""
    video_ids = []
    page_token = None
    while len(video_ids) < limit:
        resp = (
            youtube.playlistItems()
            .list(
                part="contentDetails",
                playlistId=uploads_playlist,
                maxResults=min(50, limit - len(video_ids)),
                pageToken=page_token,
            )
            .execute()
        )
        for it in resp.get("items", []):
            video_ids.append(it["contentDetails"]["videoId"])
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    rows = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        resp = (
            youtube.videos()
            .list(part="snippet,statistics", id=",".join(chunk))
            .execute()
        )
        for v in resp.get("items", []):
            s = v.get("statistics", {})
            rows.append(
                {
                    "video_id": v["id"],
                    "title": v["snippet"]["title"],
                    "published_at": v["snippet"]["publishedAt"][:10],
                    "views": int(s.get("viewCount", 0)),
                    "likes": int(s.get("likeCount", 0)),
                    "comments": int(s.get("commentCount", 0)),
                }
            )
    rows.sort(key=lambda r: r["published_at"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# YouTube Analytics API : 스튜디오 분석 지표 (일별)
# ---------------------------------------------------------------------------
CORE_METRICS = [
    "views",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
    "subscribersGained",
    "subscribersLost",
    "likes",
    "comments",
    "shares",
]


def fetch_analytics_for_day(analytics, day):
    """특정 날짜의 채널 단위 스튜디오 지표를 dict로 반환. 데이터 없으면 None."""
    day_str = day.isoformat()
    resp = (
        analytics.reports()
        .query(
            ids="channel==MINE",
            startDate=day_str,
            endDate=day_str,
            metrics=",".join(CORE_METRICS),
        )
        .execute()
    )
    rows = resp.get("rows")
    if not rows:
        return None
    values = rows[0]
    record = {"date": day_str}
    for name, val in zip(CORE_METRICS, values):
        record[name] = val
    return record


# 참고: 노출수(impressions)·CTR 은 YouTube Analytics API(on-demand)가 제공하지 않는
# 지표라 여기서 수집하지 않는다. 필요하면 별도의 YouTube Reporting API(벌크 CSV)로
# 확장해야 한다.
ANALYTICS_COLUMNS = ["date"] + CORE_METRICS


# ---------------------------------------------------------------------------
# Google Sheets (gspread)
# ---------------------------------------------------------------------------
def open_or_create_spreadsheet(gc):
    """SHEET_ID 가 있으면 그 시트를, 없으면 제목으로 찾고, 없으면 새로 생성."""
    sheet_id = _env("SHEET_ID")
    if sheet_id:
        return gc.open_by_key(sheet_id), False

    title = _env("SHEET_TITLE", DEFAULT_SHEET_TITLE)
    try:
        return gc.open(title), False
    except gspread.SpreadsheetNotFound:
        sh = gc.create(title)
        share_email = _env("SHARE_EMAIL")
        if share_email:
            sh.share(share_email, perm_type="user", role="writer")
        return sh, True


def get_or_create_worksheet(sh, title, header):
    try:
        ws = sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=max(10, len(header)))
        ws.append_row(header, value_input_option="USER_ENTERED")
    # 헤더가 비어 있으면 채워줌
    if not ws.row_values(1):
        ws.update("A1", [header])
    return ws


def append_channel_summary(sh, summary):
    header = ["date", "subscribers", "total_views", "total_videos"]
    ws = get_or_create_worksheet(sh, "채널요약", header)
    today = date.today().isoformat()
    existing_dates = ws.col_values(1)[1:]  # 헤더 제외
    if today in existing_dates:
        print("  ℹ️ 채널요약: 오늘 날짜가 이미 있어 건너뜀")
        return
    ws.append_row(
        [today, summary["subscribers"], summary["total_views"], summary["total_videos"]],
        value_input_option="USER_ENTERED",
    )
    print("  ✅ 채널요약 1행 추가")


def overwrite_videos(sh, videos):
    header = ["video_id", "title", "published_at", "views", "likes", "comments"]
    ws = get_or_create_worksheet(sh, "영상별통계", header)
    ws.clear()
    rows = [header] + [
        [v["video_id"], v["title"], v["published_at"], v["views"], v["likes"], v["comments"]]
        for v in videos
    ]
    ws.update("A1", rows, value_input_option="USER_ENTERED")
    print(f"  ✅ 영상별통계 {len(videos)}개 영상 갱신")


def append_analytics(sh, analytics):
    ws = get_or_create_worksheet(sh, "스튜디오분석", ANALYTICS_COLUMNS)
    existing_dates = set(ws.col_values(1)[1:])

    today = date.today()
    new_rows = []
    for delta in range(ANALYTICS_LOOKBACK_DAYS, 0, -1):
        day = today - timedelta(days=delta)
        if day.isoformat() in existing_dates:
            continue
        record = fetch_analytics_for_day(analytics, day)
        if record is None:
            continue
        new_rows.append([record.get(col, "") for col in ANALYTICS_COLUMNS])

    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")
        print(f"  ✅ 스튜디오분석 {len(new_rows)}일치 추가")
    else:
        print("  ℹ️ 스튜디오분석: 추가할 새 날짜 데이터 없음")


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main():
    print("🔐 OAuth 인증 중...")
    creds = build_credentials()

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)
    gc = gspread.authorize(creds)

    print("📺 채널 공개 통계 수집 중...")
    target_id = resolve_target_channel_id(youtube)
    authorized_id = get_authorized_channel_id(youtube)
    summary, uploads_playlist = fetch_channel_summary(youtube, target_id)
    print(
        f"   채널: {summary['title']} / 구독자 {summary['subscribers']:,} / "
        f"총 조회수 {summary['total_views']:,} / 영상 {summary['total_videos']:,}개"
    )

    print("🎬 영상별 통계 수집 중...")
    videos = fetch_recent_videos(youtube, uploads_playlist)
    print(f"   최근 영상 {len(videos)}개 수집")

    print("📊 시트 준비...")
    sh, created = open_or_create_spreadsheet(gc)
    if created:
        print(f"   🆕 새 스프레드시트 생성: {sh.title}")
    print(f"   📄 시트 URL: {sh.url}")

    append_channel_summary(sh, summary)
    overwrite_videos(sh, videos)

    # 스튜디오 분석(시청시간 등)은 토큰이 대상 채널 소유자로 인증된 경우에만 가능.
    effective_target = target_id or authorized_id
    if effective_target and effective_target == authorized_id:
        print("📊 스튜디오 분석 지표 수집 중...")
        append_analytics(sh, analytics)
    else:
        print("  ⏭️ 스튜디오분석 건너뜀: 토큰이 대상 채널 소유자로 인증돼 있지 않습니다.")
        print(f"     (인증 채널={authorized_id}, 대상 채널={effective_target})")
        print("     → 공개 통계만 수집했습니다. 분석 지표는 대상 채널로 토큰 재발급이 필요합니다.")

    print("🎉 완료!")
    print(f"👉 {sh.url}")


if __name__ == "__main__":
    main()
