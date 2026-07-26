"""
레딧 달바(d'alba / dalba) 언급 수집기 (Apify → 웹사이트 데이터)

레딧에서 "d'alba", "dalba", "달바" 가 언급된 글과 그 글의 댓글을 매일 모아
한 곳에서 볼 수 있게 정리한다.

  1) 글 검색   : 제목·본문에 키워드가 들어간 글
  2) 댓글 검색 : **레딧 전체 댓글**에서 키워드가 들어간 댓글

2)가 핵심이다. 브랜드 언급은 "세럼 추천 좀" 같은 남의 글 댓글에 묻혀 있는 경우가
많아서, 글 검색만 하면 절반 이상을 놓친다. Reddit Scraper Lite 는 댓글 검색을
지원하므로 두 가지를 검색 한 번으로 같이 가져온다.

비용은 maxItems(결과 수 상한)로 통제한다. 결과 1건당 과금이라 상한이 곧 비용 상한이다.

레딧 공식 API 를 쓰지 않는 이유:
  2026년부터 Responsible Builder Policy 로 신규 API 발급이 수동 승인제가 되었고,
  승인까지 며칠~몇 주가 걸리며 거절되는 경우도 많다. Apify 는 승인이 필요 없다.

결과는 `web/data/mentions.json` 에 **최신순으로 누적**된다. 이미 수집한 글/댓글
ID 는 건너뛰므로 중복이 생기지 않는다. (하루 실패해도 다음 날 일주일치를 다시
훑어 메꾸는 구조) 이 파일이 커밋/푸시되면 Vercel 이 웹사이트를 자동 재배포한다.

환경변수(GitHub Actions Secrets/Variables 로 주입):
  APIFY_TOKEN          : Apify API 토큰               (필수, 인스타 수집기와 같은 것)
  APIFY_ACTOR          : 사용할 액터                  (선택, 기본 trudax/reddit-scraper-lite)
  QUERIES              : 검색어 목록(쉼표 구분)        (선택, 기본 아래 DEFAULT_QUERIES)
  TIME_FILTER          : 검색 기간 hour/day/week/month (선택, 기본 "week")
  MAX_ITEMS            : 한 번에 받을 최대 결과 수      (선택, 기본 200 — 그대로 비용 상한)
  INCLUDE_THREAD_COMMENTS : "1" 이면 언급 글의 반응 댓글까지 (선택, 기본 0)
  WEB_DATA_PATH        : 웹 데이터 JSON 경로          (선택, 기본 ../web/data/mentions.json)
  MAX_ROWS             : 보관할 최대 항목 수           (선택, 기본 5000)
  ONLY_RELEVANT        : "1" 이면 무관해 보이는 건 제외 (선택, 기본 0 = 전부 저장)
  SHEET_ID             : 구글 시트에도 쓸 때만 지정     (선택, 기본 사용 안 함)
  GOOGLE_CREDENTIALS   : 구글 서비스계정 JSON 문자열    (선택, SHEET_ID 와 함께 필요)
  OUTPUT_TAB           : 결과 탭 이름                 (선택, 기본 "레딧언급")
"""

import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

from apify_client import ApifyClient

KST = timezone(timedelta(hours=9))

DEFAULT_ACTOR = "trudax/reddit-scraper-lite"

# 검색어. 레딧 검색은 아포스트로피를 잘 못 다루므로 여러 형태로 던지고,
# 실제 판정은 아래 KEYWORD_PATTERNS 정규식으로 다시 한 번 거른다.
DEFAULT_QUERIES = ["dalba", "d'alba", "dalba white truffle", "달바"]

# 액터 요금 (trudax/reddit-scraper-lite, 무료 티어 기준 $3.40/1000건).
# 유료 플랜은 이보다 싸므로 실제 청구액은 이 값보다 낮게 나온다.
# 실행 후 대략적인 감을 잡기 위한 값일 뿐이니 정확한 금액은 Apify 콘솔에서 확인할 것.
COST_PER_1K_RESULTS = 3.40

# "dalba", "d'alba", "d’alba", "D Alba", "달바" 를 모두 잡는다.
# 앞뒤를 (?<![a-z0-9]) / (?![a-z0-9]) 로 막아 "albatross", "hedalbaz" 같은 건
# 걸리지 않으면서, URL 슬러그("/dalba_review") 처럼 밑줄이 붙은 형태는 잡는다.
KEYWORD_PATTERNS = [
    ("d'alba", re.compile(r"(?<![a-z0-9])d\s*['’ʼ`]?\s*alba(?![a-z0-9])", re.IGNORECASE)),
    ("달바", re.compile(r"달바")),
]

# 관련도 판정용. 뷰티 맥락이면 브랜드 얘기일 확률이 높다.
# (dalba 는 이탈리아 성씨이기도 해서 축구/인명 글이 섞여 들어온다)
BEAUTY_SUBREDDITS = {
    "asianbeauty",
    "asianbeautyadvice",
    "skincareaddiction",
    "skincareaddicts",
    "skincare_addiction",
    "skincareaddictionuk",
    "koreanbeauty",
    "kbeauty",
    "skincarefree",
    "30plusskincare",
    "sephora",
    "beauty",
    "beautyguruchatter",
    "tretinoin",
    "makeupaddiction",
    "indianskincareaddicts",
    "ausskincare",
    "beautytalkph",
    "muacjdiscussion",
}

BEAUTY_TERMS = re.compile(
    r"(skin ?care|skincare|serum|sunscreen|spf|essence|toner|moisturi[sz]er|cleanser|"
    r"ampoule|truffle|k-?beauty|korean|retinol|niacinamide|hyaluronic|sephora|olive ?young|"
    r"routine|pores?|acne|glow|mist|spray|세럼|스킨케어|선크림|화장품|앰플)",
    re.IGNORECASE,
)

HEADER = [
    "날짜(KST)",
    "종류",
    "서브레딧",
    "제목",
    "내용",
    "작성자",
    "점수",
    "댓글수",
    "관련도",
    "매칭키워드",
    "링크",
    "ID",
]
ID_COL = len(HEADER)  # ID 는 마지막 열

BODY_LIMIT = 1500

# 웹사이트(Vercel)가 읽는 데이터 파일. 리포지토리 안에 커밋되며,
# 푸시되면 Vercel 이 자동으로 다시 배포한다.
DEFAULT_WEB_DATA = os.path.join(os.path.dirname(__file__), "..", "web", "data", "mentions.json")


# ---------------------------------------------------------------------------
# 환경변수 헬퍼
# ---------------------------------------------------------------------------
def _env(name, default=None):
    """환경변수를 읽되 비어 있으면(빈 문자열 포함) default 를 돌려준다."""
    value = os.environ.get(name)
    return value if value else default


def _int_env(name, default):
    try:
        return int(_env(name, default))
    except (TypeError, ValueError):
        return default


def _list_env(name, default):
    raw = _env(name)
    if not raw:
        return list(default)
    if raw.strip().lower() in {"none", "off", "-"}:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


# ---------------------------------------------------------------------------
# 키워드 판정
# ---------------------------------------------------------------------------
def matched_keywords(*texts):
    """주어진 텍스트들에서 매칭된 키워드 이름 목록을 돌려준다. 없으면 빈 리스트."""
    blob = " ".join(t for t in texts if t)
    if not blob:
        return []
    return [name for name, pattern in KEYWORD_PATTERNS if pattern.search(blob)]


def judge_relevance(subreddit, *texts):
    """뷰티 서브레딧이거나 뷰티 단어가 같이 나오면 '관련', 아니면 '확인필요'.
    (dalba 는 이탈리아 성씨라 무관한 글이 섞이므로 버리지 않고 표시만 한다)"""
    if (subreddit or "").lower() in BEAUTY_SUBREDDITS:
        return "관련"
    blob = " ".join(t for t in texts if t)
    return "관련" if BEAUTY_TERMS.search(blob) else "확인필요"


def clean_text(text, limit=BODY_LIMIT):
    text = (text or "").replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"\s{2,}", " ", text)
    if len(text) > limit:
        text = text[:limit] + "…"
    return text


# ---------------------------------------------------------------------------
# Apify 응답 읽기
#
# 액터마다 필드 이름이 조금씩 다르고 버전이 올라가며 바뀌기도 한다.
# 그래서 후보 키를 여러 개 두고 먼저 잡히는 값을 쓴다.
# (인스타 수집기의 get_views 와 같은 방식)
# ---------------------------------------------------------------------------
def _first(item, *keys, default=None):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return default


def _parse_ts(value):
    """epoch 초 또는 ISO 문자열을 epoch 초(int)로 바꾼다. 못 읽으면 0."""
    if isinstance(value, (int, float)):
        # 밀리초로 오는 액터도 있다
        return int(value / 1000) if value > 10_000_000_000 else int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return _parse_ts(int(text))
        try:
            return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return 0
    return 0


def _strip_sub(name):
    """'r/AsianBeauty' / '/r/AsianBeauty' → 'AsianBeauty'"""
    return re.sub(r"^/?r/", "", (name or "").strip(), flags=re.IGNORECASE)


def is_comment(item):
    """댓글이면 True. dataType 이 있으면 그걸 믿고, 없으면 모양으로 판단한다."""
    kind = (_first(item, "dataType", "type", default="") or "").lower()
    if kind in {"comment", "t1"}:
        return True
    if kind in {"post", "submission", "t3"}:
        return False
    # 제목이 없고 본문 + 소속 글 ID 가 있으면 댓글로 본다
    return not _first(item, "title") and bool(
        _first(item, "postId", "parentId", "postTitle", "linkId")
    )


def post_to_item(post, kinds):
    """Apify 글 아이템 → 표준 항목(dict)"""
    subreddit = _strip_sub(
        _first(post, "subreddit", "communityName", "parsedCommunityName", default="")
    )
    title = _first(post, "title", default="")
    body = _first(post, "selfText", "selftext", "body", "text", default="")
    ts = _parse_ts(_first(post, "createdAt", "created_utc", "createdUtc", "created"))
    post_id = _first(post, "id", "parsedId", "postId", default="")
    return {
        "id": f"t3_{post_id}",
        "ts": ts,
        "date": datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M"),
        "kind": "포스트",
        "subreddit": subreddit,
        "title": clean_text(title, 300),
        "body": clean_text(body),
        "author": _first(post, "author", "username", default=""),
        "score": _first(post, "score", "upVotes", "ups", default=0),
        "comments": _first(post, "numComments", "numberOfComments", "commentCount", default=0),
        "relevance": judge_relevance(subreddit, title, body),
        "keywords": kinds,
        "url": _first(post, "url", "link", "permalink", default=""),
    }


def comment_to_item(comment, kinds, kind_label, post):
    """Apify 댓글 아이템 → 표준 항목(dict). post 는 댓글이 달린 글(없으면 None)."""
    subreddit = _strip_sub(
        _first(comment, "subreddit", "communityName", default="")
    ) or (post or {}).get("subreddit", "")
    body = _first(comment, "body", "text", "comment", default="")
    title = _first(comment, "postTitle", "linkTitle", default="") or (post or {}).get("title", "")
    ts = _parse_ts(_first(comment, "createdAt", "created_utc", "createdUtc", "created"))
    comment_id = _first(comment, "id", "parsedId", default="")

    url = _first(comment, "url", "permalink", "link", default="")
    if not url:
        # 액터가 댓글 링크를 안 주면 글 주소 + 댓글 ID 로 만든다
        post_url = (post or {}).get("url", "")
        url = f"{post_url.rstrip('/')}/{comment_id}/" if post_url else ""

    return {
        "id": f"t1_{comment_id}",
        "ts": ts,
        "date": datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M"),
        "kind": kind_label,
        "subreddit": subreddit,
        "title": clean_text(title, 300),
        "body": clean_text(body),
        "author": _first(comment, "author", "username", default=""),
        "score": _first(comment, "score", "upVotes", "ups", default=0),
        "comments": "",
        "relevance": judge_relevance(subreddit, title, body),
        "keywords": kinds,
        "url": url,
    }


def to_row(item):
    """표준 항목을 CSV/시트 행으로 변환. (HEADER 순서와 1:1)"""
    return [
        item["date"],
        item["kind"],
        f"r/{item['subreddit']}" if item["subreddit"] else "",
        item["title"],
        item["body"],
        item["author"],
        item["score"],
        item["comments"],
        item["relevance"],
        ", ".join(item["keywords"]),
        item["url"],
        item["id"],
    ]


# ---------------------------------------------------------------------------
# Apify 수집
# ---------------------------------------------------------------------------
def build_apify_client():
    token = _env("APIFY_TOKEN")
    if not token:
        raise ValueError(
            "APIFY_TOKEN 환경변수가 비어 있습니다. "
            "인스타 수집기에 쓰는 것과 같은 Apify 토큰을 Secret 으로 주입하세요."
        )
    return ApifyClient(token)


def _run_dataset_id(run):
    """apify-client 버전에 따라 run 이 dict 또는 객체로 온다. 둘 다에서 꺼낸다."""
    if isinstance(run, dict):
        return run.get("defaultDatasetId") or run.get("default_dataset_id")
    for attr in ("default_dataset_id", "defaultDatasetId"):
        value = getattr(run, attr, None)
        if value:
            return value
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


def _run_actor(client, actor_id, run_input, label):
    """액터를 한 번 실행하고 결과 아이템 리스트를 돌려준다. 실패해도 죽지 않는다."""
    print(f"🚀 {label}")
    try:
        run = client.actor(actor_id).call(run_input=run_input)
    except Exception as e:  # noqa: BLE001 — 액터 오류로 전체가 멈추지 않게 한다
        print(f"   ⚠️ 액터 실행 실패: {e}")
        return []

    dataset_id = _run_dataset_id(run)
    if not dataset_id:
        print(f"   ⚠️ 데이터셋 ID 를 찾지 못했습니다: {run!r}")
        return []

    items = list(client.dataset(dataset_id).iterate_items())
    print(f"   아이템 {len(items)}개 수신")
    return items


def collect(client, actor_id, queries, time_filter, max_items, include_thread_comments):
    """검색 한 번으로 글과 댓글을 모두 모은다.

    Reddit Scraper Lite 는 레딧 **전체 댓글 검색**을 지원한다. 브랜드 언급은
    "세럼 추천 좀" 같은 남의 글 댓글에 묻혀 있는 경우가 많아, 이게 글 검색보다
    중요하다. maxItems 가 결과 수를 자르므로 그대로 비용 상한이 된다.

    include_thread_comments=True 면 검색에 걸린 글의 댓글까지 딸려 온다.
    (같은 maxItems 예산을 나눠 쓰는 셈이라 언급 자체는 덜 잡힐 수 있어 기본은 끔)

    반환: ({ID: item}, 수신 결과 수)
    """
    raw_items = _run_actor(
        client,
        actor_id,
        {
            "searches": queries,
            "searchPosts": True,
            "searchComments": True,   # ← 핵심. 남의 스레드에 묻힌 언급을 잡는다
            "searchCommunities": False,
            "searchUsers": False,
            "sort": "new",
            "time": time_filter,
            "maxItems": max_items,
            # 검색에 걸린 글의 댓글까지 통째로 긁으면 예산이 그쪽으로 다 샌다
            "skipComments": not include_thread_comments,
            "skipUserPosts": True,
            "includeNSFW": True,
        },
        f"검색: {', '.join(queries)} (최근 {time_filter}, 최대 {max_items}건)",
    )

    found = {}
    dropped = 0
    for raw in raw_items:
        if is_comment(raw):
            body = _first(raw, "body", "text", "comment")
            kinds = matched_keywords(body)
            if kinds:
                item = comment_to_item(raw, kinds, "댓글(언급)", None)
            elif include_thread_comments:
                # 언급 글에 달린 반응 댓글. 맥락으로 같이 본다.
                item = comment_to_item(raw, ["(스레드 반응)"], "댓글(반응)", None)
            else:
                dropped += 1
                continue
        else:
            kinds = matched_keywords(
                _first(raw, "title"), _first(raw, "selfText", "selftext", "body", "text")
            )
            # 검색은 느슨해서 무관한 글도 섞여 온다("Alba Botanica" 등)
            if not kinds:
                dropped += 1
                continue
            item = post_to_item(raw, kinds)

        if item["id"] in ("t3_", "t1_"):  # ID 를 못 읽은 항목은 버린다
            dropped += 1
            continue
        found.setdefault(item["id"], item)

    posts = sum(1 for i in found.values() if i["kind"] == "포스트")
    print(f"   글 {posts}건 / 댓글 {len(found) - posts}건 (무관·중복 {dropped}건 제외)")
    return found, len(raw_items)


# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------
def save_csv(items, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(to_row(it) for it in items)
    print(f"💾 CSV 저장: {path} ({len(items)}행)")


def save_web_json(items, path, max_items):
    """웹사이트가 읽는 JSON 을 갱신한다.

    기존 파일과 합쳐 ID 기준으로 중복을 없애고, 최신순으로 정렬해 max_items 까지만
    남긴다. 이 파일이 커밋/푸시되면 Vercel 이 자동으로 다시 배포한다.
    반환값은 (신규 건수, 전체 건수).
    """
    path = os.path.abspath(path)
    existing = []
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                existing = (json.load(f) or {}).get("items") or []
        except (ValueError, OSError) as e:
            print(f"   ⚠️ 기존 JSON 을 읽지 못해 새로 만듭니다: {e}")

    merged = {it["id"]: it for it in existing}
    new_count = sum(1 for it in items if it["id"] not in merged)
    for it in items:
        merged[it["id"]] = it  # 점수/댓글수는 최신값으로 갱신

    ordered = sorted(merged.values(), key=lambda it: it.get("ts") or 0, reverse=True)
    if max_items:
        ordered = ordered[:max_items]

    payload = {
        "updatedAt": datetime.now(KST).isoformat(timespec="seconds"),
        "total": len(ordered),
        "items": ordered,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"🌐 웹 데이터 저장: {path} (신규 {new_count}건 / 전체 {len(ordered)}건)")
    return new_count, len(ordered)


def build_gspread_client():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_json:
        return None
    import gspread  # 시트를 쓸 때만 필요

    return gspread.service_account_from_dict(json.loads(creds_json))


def write_to_sheet(gc, sheet_id, tab_name, items, max_rows):
    """이미 있는 ID 는 건너뛰고, 새 행만 최신순으로 맨 위에 끼워 넣는다."""
    import gspread

    sh = gc.open_by_key(sheet_id)
    print(f"   📄 시트: {sh.title} / {sh.url}")

    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=len(HEADER))
        ws.update(range_name="A1", values=[HEADER], value_input_option="USER_ENTERED")

    existing_ids = set(ws.col_values(ID_COL)[1:])  # 헤더 제외
    fresh = [to_row(it) for it in items if it["id"] not in existing_ids]
    if not fresh:
        print("   새로 추가할 항목이 없습니다(모두 이미 수집됨).")
        return 0

    ws.insert_rows(fresh, row=2, value_input_option="USER_ENTERED")
    print(f"   ✅ {len(fresh)}건 추가 (기존 {len(existing_ids)}건 유지)")

    total = len(existing_ids) + len(fresh) + 1
    if max_rows and total > max_rows + 1:
        ws.delete_rows(max_rows + 2, total)
        print(f"   🧹 오래된 행 정리: 최대 {max_rows}행 유지")
    return len(fresh)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main():
    actor_id = _env("APIFY_ACTOR", DEFAULT_ACTOR)
    queries = _list_env("QUERIES", DEFAULT_QUERIES)
    time_filter = _env("TIME_FILTER", "week")
    max_items = _int_env("MAX_ITEMS", 200)
    include_thread_comments = _env("INCLUDE_THREAD_COMMENTS", "0") == "1"
    max_rows = _int_env("MAX_ROWS", 5000)
    only_relevant = _env("ONLY_RELEVANT", "0") == "1"

    if not queries:
        raise ValueError("QUERIES 가 비어 있습니다. 검색어를 최소 하나는 지정하세요.")

    client = build_apify_client()
    print(f"🎬 액터: {actor_id}")

    collected, received = collect(
        client, actor_id, queries, time_filter, max_items, include_thread_comments
    )
    items = list(collected.values())
    if only_relevant:
        before = len(items)
        items = [it for it in items if it["relevance"] == "관련"]
        print(f"🧹 관련도 필터: {before} → {len(items)}건")

    items.sort(key=lambda it: it.get("ts") or 0, reverse=True)

    if not items:
        print("😶 이번 실행에서 찾은 언급이 없습니다.")

    stamp = datetime.now(KST).strftime("%Y-%m-%d")
    save_csv(items, os.path.join("output", f"reddit_dalba_{stamp}.csv"))

    # 웹사이트용 JSON (기본 출력). 커밋되면 Vercel 이 자동 배포한다.
    save_web_json(items, _env("WEB_DATA_PATH", DEFAULT_WEB_DATA), max_rows)

    # 구글 시트는 선택 사항. SHEET_ID + GOOGLE_CREDENTIALS 가 있을 때만 기록한다.
    sheet_id = _env("SHEET_ID")
    gc = build_gspread_client() if sheet_id else None
    added = None
    if sheet_id and gc:
        print("🔐 구글 시트에도 기록 중...")
        added = write_to_sheet(gc, sheet_id, _env("OUTPUT_TAB", "레딧언급"), items, max_rows)

    relevant = sum(1 for it in items if it["relevance"] == "관련")
    posts = sum(1 for it in items if it["kind"] == "포스트")
    cost = received / 1000 * COST_PER_1K_RESULTS
    print(
        f"🎉 완료! 수집 {len(items)}건 "
        f"(글 {posts} / 댓글 {len(items) - posts}, "
        f"관련 {relevant} / 확인필요 {len(items) - relevant})"
        + (f", 시트 신규 {added}건" if added is not None else "")
    )
    print(
        f"💰 이번 실행 예상 비용 최대 약 ${cost:.2f} (결과 {received}건 × "
        f"${COST_PER_1K_RESULTS}/1000). 유료 플랜은 더 저렴하니 실제 금액은 "
        "Apify 콘솔에서 확인하세요."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"❌ 실패: {e}", file=sys.stderr)
        raise
