"""
Threads(메타) 게시물 수집기 — 문체 분석용

지정한 Threads 핸들의 최근 게시물을 Apify 액터로 수집해, 본문과
인게이지먼트(좋아요/댓글/리포스트/인용)를 실행 로그로 출력한다.
(구글 시트 저장 없이 로그로만 — 일회성 문체 분석 목적)

환경변수:
  APIFY_TOKEN     : Apify API 토큰 (필수)
  THREADS_HANDLE  : 수집할 핸들(@ 없이). 기본 "usa.mminz"
  MAX_POSTS       : 계정당 최대 수집 글 수. 기본 40 (비용 상한)
  THREADS_ACTOR   : 사용할 액터. 기본 "automation-lab/threads-scraper"
"""

import os
from datetime import datetime, timezone

from apify_client import ApifyClient

DEFAULT_ACTOR = "automation-lab/threads-scraper"


def _env(name, default=None):
    value = os.environ.get(name)
    return value if value else default


def _run_dataset_id(run):
    """apify-client 버전차 대응: dict/객체/pydantic 에서 dataset id 추출."""
    if isinstance(run, dict):
        return run.get("defaultDatasetId") or run.get("default_dataset_id")
    for attr in ("default_dataset_id", "defaultDatasetId"):
        val = getattr(run, attr, None)
        if val:
            return val
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


def _first(item, *keys):
    """여러 후보 키 중 처음으로 값이 있는 것을 반환(중첩 키는 'a.b' 표기)."""
    for key in keys:
        cur = item
        ok = True
        for part in key.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return None


def _text_of(item):
    return _first(item, "text", "caption", "post_text", "content") or ""


def _int_of(item, *keys):
    val = _first(item, *keys)
    return int(val) if isinstance(val, (int, float)) else 0


def _date_of(item):
    iso = _first(item, "date", "publishedAt", "timestampIso")
    if iso:
        return str(iso)[:10]
    ts = _first(item, "timestamp", "taken_at", "takenAt")
    if isinstance(ts, (int, float)):
        # 초 단위 유닉스 타임스탬프 가정
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    return ""


def _url_of(item, handle):
    url = _first(item, "url", "postUrl", "permalink")
    if url:
        return url
    code = _first(item, "code", "shortcode", "pk")
    if code:
        return f"https://www.threads.com/@{handle}/post/{code}"
    return ""


def main():
    handle = (_env("THREADS_HANDLE", "usa.mminz") or "").lstrip("@").strip()
    max_posts = int(_env("MAX_POSTS", "40"))
    actor_id = _env("THREADS_ACTOR", DEFAULT_ACTOR)

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise ValueError("APIFY_TOKEN 환경변수가 비어 있습니다.")

    client = ApifyClient(token)
    run_input = {
        "mode": "posts",
        "usernames": [handle],
        "maxPosts": max_posts,
        "includeProfile": True,
    }
    print(f"🚀 Threads 수집: {actor_id} / @{handle} / 최대 {max_posts}글")
    run = client.actor(actor_id).call(run_input=run_input)
    dataset_id = _run_dataset_id(run)
    if not dataset_id:
        raise RuntimeError(f"데이터셋 ID 를 찾지 못했습니다: {run!r}")

    items = list(client.dataset(dataset_id).iterate_items())
    print(f"   데이터셋 아이템 {len(items)}개 수신")

    # 스키마 확인용: 첫 아이템 키 덤프
    if items:
        print("🔎 첫 아이템 키:", sorted(items[0].keys()))

    # 프로필과 게시물 분리
    posts = []
    profile = None
    for it in items:
        if _text_of(it):
            posts.append(it)
        elif _first(it, "followersCount", "follower_count", "biography", "bio"):
            profile = it

    if profile:
        print("\n=== PROFILE ===")
        print("username:", _first(profile, "username", "handle"))
        print("followers:", _first(profile, "followersCount", "follower_count"))
        print("bio:", _first(profile, "biography", "bio"))

    print(f"\n=== POSTS ({len(posts)}) ===")
    for i, p in enumerate(posts, 1):
        likes = _int_of(p, "likeCount", "like_count", "likesCount")
        replies = _int_of(p, "replyCount", "repliesCount", "text_post_app_info.direct_reply_count")
        reposts = _int_of(p, "repostCount", "reposts", "text_post_app_info.repost_count")
        quotes = _int_of(p, "quoteCount", "text_post_app_info.quote_count")
        print(
            f"\n--- #{i} | {_date_of(p)} | ♥{likes} 💬{replies} 🔁{reposts} ❝{quotes} "
            f"| {_url_of(p, handle)} ---"
        )
        print(_text_of(p).strip())

    print(f"\n✅ 완료: 게시물 {len(posts)}개 출력")


if __name__ == "__main__":
    main()
