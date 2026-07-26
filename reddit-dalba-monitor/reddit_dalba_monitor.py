"""
레딧 달바(d'alba / dalba) 언급 수집기 (Apify → 웹사이트 데이터)

레딧에서 "d'alba", "dalba", "달바" 가 언급된 글과 그 글의 댓글을 매일 모아
한 곳에서 볼 수 있게 정리한다.

  1) 글 검색   : 검색어별로 레딧 전체에서 키워드가 들어간 글을 찾는다.
  2) 스레드 댓글: 1)에서 실제로 키워드가 확인된 글에 대해서만 댓글을 가져온다.
                 (키워드가 들어간 댓글 전부 + 점수 높은 반응 몇 개)

댓글을 2)에서만 가져오는 건 비용 때문이다. 서브레딧 전체 댓글을 훑으면 하루
수만 건이라 월 $100 을 넘긴다. 검색으로 걸린 글만 대상으로 하면 월 $10~20 선이다.

레딧 공식 API 를 쓰지 않는 이유:
  2026년부터 Responsible Builder Policy 로 신규 API 발급이 수동 승인제가 되었고,
  승인까지 며칠~몇 주가 걸리며 거절되는 경우도 많다. Apify 는 승인이 필요 없다.

결과는 `web/data/mentions.json` 에 **최신순으로 누적**된다. 이미 수집한 글/댓글
ID 는 건너뛰므로 중복이 생기지 않는다. (하루 실패해도 다음 날 일주일치를 다시
훑어 메꾸는 구조) 이 파일이 커밋/푸시되면 Vercel 이 웹사이트를 자동 재배포한다.

환경변수(GitHub Actions Secrets/Variables 로 주입):
  APIFY_TOKEN          : Apify API 토큰               (필수, 인스타 수집기와 같은 것)
  APIFY_ACTOR          : 사용할 액터                  (선택, 기본 automation-lab/reddit-scraper)
  QUERIES              : 검색어 목록(쉼표 구분)        (선택, 기본 아래 DEFAULT_QUERIES)
  TIME_FILTER          : 검색 기간 hour/day/week/month (선택, 기본 "week")
  MAX_POSTS_PER_QUERY  : 검색어당 최대 글 수           (선택, 기본 50 — 비용 상한)
  MAX_COMMENTS_PER_POST: 글당 최대 댓글 수             (선택, 기본 30 — 비용 상한)
  TOP_COMMENTS_PER_POST: 언급 글마다 담을 반응 댓글 수  (선택, 기본 3)
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

DEFAULT_ACTOR = "automation-lab/reddit-scraper"

# 검색어. 레딧 검색은 아포스트로피를 잘 못 다루므로 여러 형태로 던지고,
# 실제 판정은 아래 KEYWORD_PATTERNS 정규식으로 다시 한 번 거른다.
DEFAULT_QUERIES = ["dalba", "d'alba", "dalba white truffle", "달바"]

# 액터 요금 (automation-lab/reddit-scraper 기준). 실행 후 예상 비용을 찍어주기 위한 값이라
# 실제 청구액과는 다를 수 있다. 액터를 바꾸면 이 값도 같이 바꿔야 한다.
COST_PER_1K_POSTS = 1.15
COST_PER_1K_COMMENTS = 0.58

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


def search_posts(client, actor_id, queries, time_filter, max_posts):
    """검색어별로 글을 모은다. 댓글은 여기서 가져오지 않는다(비용 절감).

    반환: ({ID: (item, raw_post)}, 스크랩한 글 수)
    """
    found = {}
    scraped = 0

    for query in queries:
        items = _run_actor(
            client,
            actor_id,
            {
                "searchQuery": query,
                "sort": "new",
                "timeFilter": time_filter,
                "maxPostsPerSource": max_posts,
                "maxResults": max_posts,
                "includeComments": False,
            },
            f"글 검색: '{query}' (최근 {time_filter}, 최대 {max_posts}건)",
        )
        scraped += len(items)

        for raw in items:
            if is_comment(raw):
                continue
            # 검색은 느슨해서 무관한 글도 섞여 온다. 제목/본문에 키워드가
            # 실제로 있는 것만 남긴다.
            kinds = matched_keywords(
                _first(raw, "title"), _first(raw, "selfText", "selftext", "body")
            )
            if not kinds:
                continue
            item = post_to_item(raw, kinds)
            if item["id"] == "t3_":  # ID 를 못 읽은 항목은 버린다
                continue
            found.setdefault(item["id"], (item, raw))

        print(f"   누적 {len(found)}건")

    return found, scraped


def fetch_thread_comments(client, actor_id, posts, max_comments, top_n):
    """언급된 글의 댓글을 가져온다. 키워드가 들어간 댓글은 전부,
    나머지는 점수 높은 순 top_n 개(반응을 같이 보기 위함).

    반환: ({ID: item}, 스크랩한 댓글 수)
    """
    urls = [item["url"] for item, _raw in posts.values() if item.get("url")]
    if not urls:
        return {}, 0

    items = _run_actor(
        client,
        actor_id,
        {
            "urls": urls,
            "postUrls": urls,
            "includeComments": True,
            "maxCommentsPerPost": max_comments,
            "maxResults": len(urls) * max_comments,
        },
        f"댓글 수집: 글 {len(urls)}개 (글당 최대 {max_comments}건)",
    )

    # 어느 글의 댓글인지 이어붙이기 위한 조회표
    posts_by_id = {}
    for item, raw in posts.values():
        posts_by_id[item["id"].removeprefix("t3_")] = item

    grouped = {}
    scraped = 0
    for raw in items:
        if not is_comment(raw):
            continue
        scraped += 1
        post_id = str(_first(raw, "postId", "parentPostId", "linkId", default="") or "")
        post_id = re.sub(r"^t3_", "", post_id)
        grouped.setdefault(post_id, []).append(raw)

    result = {}
    for post_id, raws in grouped.items():
        post = posts_by_id.get(post_id)
        matched, others = [], []
        for raw in raws:
            kinds = matched_keywords(_first(raw, "body", "text", "comment"))
            (matched if kinds else others).append((raw, kinds))

        for raw, kinds in matched:
            item = comment_to_item(raw, kinds, "댓글(언급)", post)
            if item["id"] != "t1_":
                result[item["id"]] = item

        others.sort(key=lambda pair: _first(pair[0], "score", "upVotes", default=0) or 0, reverse=True)
        for raw, _kinds in others[:top_n]:
            item = comment_to_item(raw, ["(스레드 반응)"], "댓글(반응)", post)
            if item["id"] != "t1_" and item["id"] not in result:
                result[item["id"]] = item

    print(f"💬 댓글 {len(result)}건 정리 (수신 {scraped}건)")
    return result, scraped


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
    max_posts = _int_env("MAX_POSTS_PER_QUERY", 50)
    max_comments = _int_env("MAX_COMMENTS_PER_POST", 30)
    top_comments = _int_env("TOP_COMMENTS_PER_POST", 3)
    max_rows = _int_env("MAX_ROWS", 5000)
    only_relevant = _env("ONLY_RELEVANT", "0") == "1"

    if not queries:
        raise ValueError("QUERIES 가 비어 있습니다. 검색어를 최소 하나는 지정하세요.")

    client = build_apify_client()
    print(f"🎬 액터: {actor_id}")

    # 1) 글 검색
    posts, posts_scraped = search_posts(client, actor_id, queries, time_filter, max_posts)
    print(f"📝 키워드가 확인된 글 {len(posts)}건")

    # 2) 그 글들의 댓글 (검색으로 걸린 글만 → 비용 통제)
    comments, comments_scraped = ({}, 0)
    if posts:
        comments, comments_scraped = fetch_thread_comments(
            client, actor_id, posts, max_comments, top_comments
        )

    items = [item for item, _raw in posts.values()] + list(comments.values())
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
    cost = (
        posts_scraped / 1000 * COST_PER_1K_POSTS
        + comments_scraped / 1000 * COST_PER_1K_COMMENTS
    )
    print(
        f"🎉 완료! 수집 {len(items)}건 (관련 {relevant} / 확인필요 {len(items) - relevant})"
        + (f", 시트 신규 {added}건" if added is not None else "")
    )
    print(
        f"💰 이번 실행 예상 비용 약 ${cost:.2f} "
        f"(글 {posts_scraped}건 + 댓글 {comments_scraped}건). "
        "정확한 금액은 Apify 콘솔에서 확인하세요."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"❌ 실패: {e}", file=sys.stderr)
        raise
