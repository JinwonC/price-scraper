"""
레딧 달바(d'alba / dalba) 언급 수집기 (Reddit 공식 API → 웹사이트 데이터)

레딧 전체에서 "d'alba", "dalba", "달바" 가 언급된 글과 댓글을 매일 모아
한 곳에서 볼 수 있게 정리한다. 브랜드 언급은 대부분 "세럼 추천해줘" 같은
남의 글 **댓글**에 묻혀 있기 때문에, 아래 3가지 경로를 모두 훑는다.

  1) 글 검색   : 레딧 전체 검색(/search)에서 키워드가 들어간 글
  2) 스레드 댓글: 1)에서 찾은 글의 댓글 (키워드 댓글 + 상위 댓글 몇 개)
  3) 댓글 스트림: 뷰티 서브레딧들의 최신 댓글을 훑어 키워드가 있는 댓글

결과는 `web/data/mentions.json` 에 **최신순으로 누적**된다. 이미 수집한 글/댓글
ID 는 건너뛰므로 중복이 생기지 않는다. (하루 실패해도 다음 날 일주일치를 다시
훑어 메꾸는 구조) 이 파일이 커밋/푸시되면 Vercel 이 웹사이트를 자동 재배포한다.

환경변수(GitHub Actions Secrets/Variables 로 주입):
  REDDIT_CLIENT_ID     : 레딧 앱 client id            (필수)
  REDDIT_CLIENT_SECRET : 레딧 앱 secret               (필수)
  REDDIT_USER_AGENT    : User-Agent 문자열            (선택, 권장)
  REDDIT_USERNAME      : 레딧 계정 ID                 (선택, 있으면 계정 인증)
  REDDIT_PASSWORD      : 레딧 계정 비밀번호            (선택, 2단계인증 계정은 사용 불가)
  WEB_DATA_PATH        : 웹 데이터 JSON 경로          (선택, 기본 ../web/data/mentions.json)
  SHEET_ID             : 구글 시트에도 쓸 때만 지정     (선택, 기본 사용 안 함)
  GOOGLE_CREDENTIALS   : 구글 서비스계정 JSON 문자열    (선택, SHEET_ID 와 함께 필요)
  OUTPUT_TAB           : 결과 탭 이름                 (선택, 기본 "레딧언급")
  QUERIES              : 검색어 목록(쉼표 구분)        (선택, 기본 아래 DEFAULT_QUERIES)
  TIME_FILTER          : 검색 기간 hour/day/week/month (선택, 기본 "week")
  SCAN_SUBREDDITS      : 댓글 스트림을 훑을 서브레딧    (선택, 기본 아래 목록, "none" 이면 끔)
  MAX_SEARCH_PAGES     : 검색어당 최대 페이지(100건/장) (선택, 기본 3)
  MAX_COMMENT_PAGES    : 서브레딧당 최대 댓글 페이지    (선택, 기본 20)
  TOP_COMMENTS_PER_POST: 언급 글마다 담을 상위 댓글 수  (선택, 기본 3)
  MAX_ROWS             : 보관할 최대 항목 수           (선택, 기본 5000)
  ONLY_RELEVANT        : "1" 이면 무관해 보이는 건 제외 (선택, 기본 0 = 전부 저장)
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_BASE = "https://oauth.reddit.com"

KST = timezone(timedelta(hours=9))

# 검색어. 레딧 검색은 아포스트로피를 잘 못 다루므로 여러 형태로 던지고,
# 실제 판정은 아래 KEYWORD_PATTERNS 정규식으로 다시 한 번 거른다.
DEFAULT_QUERIES = ["dalba", "d'alba", "dalba white truffle", "달바"]

# 댓글 스트림을 훑을 뷰티 서브레딧들
DEFAULT_SCAN_SUBREDDITS = [
    "AsianBeauty",
    "AsianBeautyAdvice",
    "SkincareAddiction",
    "SkincareAddicts",
    "KoreanBeauty",
    "30PlusSkinCare",
    "Sephora",
    "beauty",
    "BeautyGuruChatter",
]

# "dalba", "d'alba", "d’alba", "D Alba", "달바" 를 모두 잡는다.
# 앞뒤를 (?<![a-z0-9]) / (?![a-z0-9]) 로 막아 "albatross", "hedalbaz" 같은 건
# 걸리지 않으면서, URL 슬러그("/dalba_review") 처럼 밑줄이 붙은 형태는 잡는다.
KEYWORD_PATTERNS = [
    ("d'alba", re.compile(r"(?<![a-z0-9])d\s*['’ʼ`]?\s*alba(?![a-z0-9])", re.IGNORECASE)),
    ("달바", re.compile(r"달바")),
]

# 관련도 판정용. 뷰티 맥락이면 브랜드 얘기일 확률이 높다.
# (dalba 는 이탈리아 성씨이기도 해서 축구/인명 글이 섞여 들어온다)
BEAUTY_SUBREDDITS = {s.lower() for s in DEFAULT_SCAN_SUBREDDITS} | {
    "skincare_addiction",
    "asianbeauty",
    "koreanbeauty",
    "kbeauty",
    "skincarefree",
    "tretinoin",
    "makeupaddiction",
    "indianskincareaddicts",
    "ausskincare",
    "skincareaddictionuk",
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
# 레딧 API 클라이언트
# ---------------------------------------------------------------------------
class RedditClient:
    """레딧 OAuth 클라이언트. 분당 100회 제한을 넘지 않도록 호출 간격을 둔다."""

    MIN_INTERVAL = 1.1  # 초. 분당 100회 제한(≈0.6초)보다 넉넉하게

    def __init__(self, client_id, client_secret, user_agent, username=None, password=None):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self._last_call = 0.0

        if username and password:
            data = {
                "grant_type": "password",
                "username": username,
                "password": password,
            }
            mode = f"계정 인증({username})"
        else:
            data = {"grant_type": "client_credentials"}
            mode = "앱 인증(client_credentials)"

        resp = requests.post(
            TOKEN_URL,
            auth=(client_id, client_secret),
            data=data,
            headers={"User-Agent": user_agent},
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"레딧 토큰 발급 실패 ({resp.status_code}): {resp.text[:200]}\n"
                "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET 을 확인하세요. "
                "(레딧 앱 타입은 'script' 여야 합니다)"
            )
        token = resp.json().get("access_token")
        if not token:
            raise RuntimeError(f"레딧 토큰 응답에 access_token 이 없습니다: {resp.text[:200]}")
        self.session.headers["Authorization"] = f"bearer {token}"
        print(f"🔑 레딧 인증 완료 - {mode}")

    def get(self, path, params=None, tries=3):
        """API GET. 429/5xx 는 잠깐 쉬었다가 재시도하고, 끝내 실패하면 None."""
        params = dict(params or {})
        params["raw_json"] = 1

        for attempt in range(1, tries + 1):
            wait = self.MIN_INTERVAL - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)

            try:
                resp = self.session.get(
                    f"{API_BASE}{path}", params=params, timeout=30
                )
            except requests.RequestException as e:  # 네트워크 오류
                print(f"   ⚠️ 요청 실패({attempt}/{tries}) {path}: {e}")
                time.sleep(2 * attempt)
                continue
            finally:
                self._last_call = time.monotonic()

            if resp.status_code == 200:
                self._respect_ratelimit(resp)
                try:
                    return resp.json()
                except ValueError:
                    print(f"   ⚠️ JSON 파싱 실패: {path}")
                    return None

            if resp.status_code in (429, 500, 502, 503, 504):
                retry_after = resp.headers.get("retry-after")
                delay = float(retry_after) if retry_after else 5 * attempt
                print(f"   ⏳ {resp.status_code} 응답, {delay:.0f}초 후 재시도 ({path})")
                time.sleep(delay)
                continue

            print(f"   ⚠️ {resp.status_code} 응답으로 건너뜀: {path} {resp.text[:120]}")
            return None

        return None

    @staticmethod
    def _respect_ratelimit(resp):
        """남은 호출 수가 얼마 없으면 리셋될 때까지 기다린다."""
        try:
            remaining = float(resp.headers.get("x-ratelimit-remaining", "100"))
            reset = float(resp.headers.get("x-ratelimit-reset", "0"))
        except ValueError:
            return
        if remaining < 5 and reset > 0:
            print(f"   ⏳ 레딧 호출 한도 임박, {reset:.0f}초 대기")
            time.sleep(min(reset + 1, 90))


# ---------------------------------------------------------------------------
# 수집
# ---------------------------------------------------------------------------
def _post_item(post, kinds):
    """검색으로 찾은 글 1건을 표준 항목(dict)으로 변환."""
    subreddit = post.get("subreddit") or ""
    title = post.get("title") or ""
    body = post.get("selftext") or ""
    ts = int(post.get("created_utc") or 0)
    return {
        "id": post.get("name") or f"t3_{post.get('id')}",
        "ts": ts,
        "date": datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M"),
        "kind": "포스트",
        "subreddit": subreddit,
        "title": clean_text(title, 300),
        "body": clean_text(body),
        "author": post.get("author") or "",
        "score": post.get("score") or 0,
        "comments": post.get("num_comments") or 0,
        "relevance": judge_relevance(subreddit, title, body),
        "keywords": kinds,
        "url": f"https://www.reddit.com{post.get('permalink') or ''}",
    }


def _comment_item(comment, kinds, kind_label, post_title=""):
    """댓글 1건을 표준 항목(dict)으로 변환."""
    subreddit = comment.get("subreddit") or ""
    body = comment.get("body") or ""
    title = post_title or comment.get("link_title") or ""
    ts = int(comment.get("created_utc") or 0)
    return {
        "id": comment.get("name") or f"t1_{comment.get('id')}",
        "ts": ts,
        "date": datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M"),
        "kind": kind_label,
        "subreddit": subreddit,
        "title": clean_text(title, 300),
        "body": clean_text(body),
        "author": comment.get("author") or "",
        "score": comment.get("score") or 0,
        "comments": "",
        "relevance": judge_relevance(subreddit, title, body),
        "keywords": kinds,
        "url": f"https://www.reddit.com{comment.get('permalink') or ''}",
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


def search_posts(client, queries, time_filter, max_pages):
    """레딧 전체 검색으로 키워드가 들어간 글을 모은다. {ID: (item, post)}"""
    found = {}
    for query in queries:
        print(f"🔎 글 검색: '{query}' (최근 {time_filter})")
        after = None
        page = 0
        while page < max_pages:
            page += 1
            data = client.get(
                "/search",
                {
                    "q": query,
                    "sort": "new",
                    "t": time_filter,
                    "limit": 100,
                    "type": "link",
                    "include_over_18": "on",
                    "after": after,
                },
            )
            children = ((data or {}).get("data") or {}).get("children") or []
            if not children:
                break

            for child in children:
                post = child.get("data") or {}
                post_id = post.get("name") or f"t3_{post.get('id')}"
                if post_id in found:
                    continue
                # 레딧 검색은 느슨해서 무관한 글도 섞여 온다. 제목/본문에
                # 키워드가 실제로 있는 것만 남긴다.
                kinds = matched_keywords(post.get("title"), post.get("selftext"))
                if not kinds:
                    continue
                found[post_id] = (_post_item(post, kinds), post)

            after = ((data or {}).get("data") or {}).get("after")
            if not after:
                break
        print(f"   누적 {len(found)}건")
    return found


def fetch_thread_comments(client, posts, top_n):
    """언급된 글의 댓글을 가져온다.
    - 키워드가 들어간 댓글은 전부
    - 나머지는 점수 높은 순 top_n 개 (반응을 같이 보기 위함)
    """
    items = {}
    for post_id, (_item, post) in posts.items():
        pid = post.get("id")
        if not pid:
            continue
        data = client.get(
            f"/comments/{pid}", {"limit": 100, "depth": 3, "sort": "top"}
        )
        if not isinstance(data, list) or len(data) < 2:
            continue

        comments = []
        for child in _walk_comments((data[1].get("data") or {}).get("children") or []):
            comments.append(child)

        title = post.get("title") or ""
        matched, others = [], []
        for c in comments:
            kinds = matched_keywords(c.get("body"))
            (matched if kinds else others).append((c, kinds))

        for c, kinds in matched:
            cid = c.get("name") or f"t1_{c.get('id')}"
            items[cid] = _comment_item(c, kinds, "댓글(언급)", title)

        others.sort(key=lambda x: x[0].get("score") or 0, reverse=True)
        for c, _kinds in others[:top_n]:
            cid = c.get("name") or f"t1_{c.get('id')}"
            if cid in items:
                continue
            items[cid] = _comment_item(c, ["(스레드 반응)"], "댓글(반응)", title)

    print(f"💬 언급 글의 댓글 {len(items)}건 수집")
    return items


def _walk_comments(children):
    """댓글 트리를 평탄화한다. 'more' 자리표시자는 건너뛴다."""
    for child in children:
        if child.get("kind") != "t1":
            continue
        data = child.get("data") or {}
        yield data
        replies = data.get("replies")
        if isinstance(replies, dict):
            yield from _walk_comments((replies.get("data") or {}).get("children") or [])


def scan_subreddit_comments(client, subreddits, max_pages, cutoff):
    """뷰티 서브레딧의 최신 댓글 스트림을 훑어 키워드가 있는 댓글만 남긴다.
    브랜드 언급 대부분이 남의 글 댓글에 있기 때문에 이 경로가 핵심이다."""
    items = {}
    for sub in subreddits:
        after = None
        page = 0
        hits = 0
        oldest = None
        while page < max_pages:
            page += 1
            data = client.get(
                f"/r/{sub}/comments", {"limit": 100, "after": after}
            )
            children = ((data or {}).get("data") or {}).get("children") or []
            if not children:
                break

            reached_cutoff = False
            for child in children:
                c = child.get("data") or {}
                created = c.get("created_utc") or 0
                oldest = created
                if created and created < cutoff:
                    reached_cutoff = True
                    continue
                kinds = matched_keywords(c.get("body"))
                if not kinds:
                    continue
                cid = c.get("name") or f"t1_{c.get('id')}"
                if cid in items:
                    continue
                items[cid] = _comment_item(c, kinds, "댓글(발견)")
                hits += 1

            if reached_cutoff:
                break
            after = ((data or {}).get("data") or {}).get("after")
            if not after:
                break

        span = ""
        if oldest:
            age_h = (time.time() - oldest) / 3600
            span = f", 최근 {age_h:.0f}시간 훑음"
        print(f"   r/{sub}: {hits}건 (페이지 {page}{span})")
    print(f"💬 서브레딧 댓글 스트림에서 {len(items)}건 발견")
    return items


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
    client_id = _env("REDDIT_CLIENT_ID")
    client_secret = _env("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError(
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET 이 비어 있습니다. "
            "https://www.reddit.com/prefs/apps 에서 'script' 앱을 만들고 "
            "GitHub Secrets 에 등록하세요. (README 참고)"
        )

    user_agent = _env(
        "REDDIT_USER_AGENT", "script:dalba-reddit-monitor:1.0 (by /u/dalba_monitor)"
    )
    queries = _list_env("QUERIES", DEFAULT_QUERIES)
    time_filter = _env("TIME_FILTER", "week")
    subreddits = _list_env("SCAN_SUBREDDITS", DEFAULT_SCAN_SUBREDDITS)
    max_search_pages = _int_env("MAX_SEARCH_PAGES", 3)
    max_comment_pages = _int_env("MAX_COMMENT_PAGES", 20)
    top_comments = _int_env("TOP_COMMENTS_PER_POST", 3)
    max_rows = _int_env("MAX_ROWS", 5000)
    only_relevant = _env("ONLY_RELEVANT", "0") == "1"

    client = RedditClient(
        client_id,
        client_secret,
        user_agent,
        _env("REDDIT_USERNAME"),
        _env("REDDIT_PASSWORD"),
    )

    # 1) 글 검색
    posts = search_posts(client, queries, time_filter, max_search_pages)
    print(f"📝 언급된 글 {len(posts)}건")

    # 2) 그 글들의 댓글
    comments = {}
    if posts:
        comments.update(fetch_thread_comments(client, posts, top_comments))

    # 3) 뷰티 서브레딧 최신 댓글 스트림
    if subreddits:
        window_days = {"hour": 1, "day": 2, "week": 8, "month": 31}.get(time_filter, 8)
        cutoff = time.time() - window_days * 86400
        print(f"🔎 서브레딧 댓글 스캔: {len(subreddits)}개 (최근 {window_days}일)")
        comments.update(
            scan_subreddit_comments(client, subreddits, max_comment_pages, cutoff)
        )

    items = [item for item, _post in posts.values()] + list(comments.values())
    if only_relevant:
        before = len(items)
        items = [it for it in items if it["relevance"] == "관련"]
        print(f"🧹 관련도 필터: {before} → {len(items)}건")

    # 최신순 정렬
    items.sort(key=lambda it: it.get("ts") or 0, reverse=True)

    if not items:
        print("😶 이번 실행에서 새로 찾은 언급이 없습니다.")

    stamp = datetime.now(KST).strftime("%Y-%m-%d")
    save_csv(items, os.path.join("output", f"reddit_dalba_{stamp}.csv"))

    # 웹사이트용 JSON (기본 출력). 커밋되면 Vercel 이 자동 배포한다.
    web_path = _env("WEB_DATA_PATH", DEFAULT_WEB_DATA)
    save_web_json(items, web_path, max_rows)

    # 구글 시트는 선택 사항. SHEET_ID + GOOGLE_CREDENTIALS 가 있을 때만 기록한다.
    sheet_id = _env("SHEET_ID")
    gc = build_gspread_client() if sheet_id else None
    added = None
    if sheet_id and gc:
        print("🔐 구글 시트에도 기록 중...")
        added = write_to_sheet(gc, sheet_id, _env("OUTPUT_TAB", "레딧언급"), items, max_rows)

    relevant = sum(1 for it in items if it["relevance"] == "관련")
    print(
        f"🎉 완료! 수집 {len(items)}건 (관련 {relevant} / 확인필요 {len(items) - relevant})"
        + (f", 시트 신규 {added}건" if added is not None else "")
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"❌ 실패: {e}", file=sys.stderr)
        raise
