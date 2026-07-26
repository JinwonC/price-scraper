# 레딧 달바 언급 수집기 (Reddit API → 구글 시트)

레딧에서 **d'alba / dalba / 달바** 가 언급된 글과 댓글을 매일 자동으로 모아
한 시트에서 볼 수 있게 정리합니다.

## 왜 이렇게 만들었나

브랜드 언급은 "달바 리뷰"처럼 제목에 대놓고 있는 글보다,
**"세럼 추천 좀" 같은 남의 글 댓글에** 훨씬 많이 묻혀 있습니다.
그래서 3가지 경로를 모두 훑습니다.

| 경로 | 무엇을 가져오나 | 시트의 `종류` |
| --- | --- | --- |
| 1. 글 검색 | 레딧 전체에서 제목·본문에 키워드가 있는 글 | `포스트` |
| 2. 스레드 댓글 | 1)에서 찾은 글의 댓글 중 키워드가 있는 것 + 점수 높은 반응 몇 개 | `댓글(언급)` / `댓글(반응)` |
| 3. 댓글 스트림 | 뷰티 서브레딧들의 최신 댓글을 훑어 키워드가 있는 댓글 | `댓글(발견)` |

3번이 사실상 핵심입니다. r/AsianBeauty, r/SkincareAddiction 등의 최신 댓글을
시간 역순으로 훑어 키워드가 나온 댓글만 건집니다.

## 결과 시트

`레딧언급` 탭에 **최신순으로 위에 쌓입니다.** 이미 수집한 글/댓글 ID 는 건너뛰므로
매일 돌려도 중복이 생기지 않습니다. 하루 실패해도 다음 날 일주일치를 다시 훑어 메꿉니다.

| 열 | 설명 |
| --- | --- |
| 날짜(KST) | 작성 시각 (한국시간) |
| 종류 | 포스트 / 댓글(언급) / 댓글(반응) / 댓글(발견) |
| 서브레딧 | `r/AsianBeauty` 형태 |
| 제목 | 글 제목 (댓글이면 달린 글의 제목) |
| 내용 | 본문·댓글 내용 (최대 1500자) |
| 작성자 / 점수 / 댓글수 | 레딧 지표 |
| 관련도 | `관련` 또는 `확인필요` |
| 매칭키워드 | 어떤 표기로 걸렸는지 |
| 링크 | 바로 가기 |
| ID | 중복 방지용 (건드리지 마세요) |

> **`확인필요` 는 왜 있나요?**
> `Dalba` 는 이탈리아 성씨이기도 해서 축구·인명 글이 섞여 들어옵니다.
> 뷰티 서브레딧이거나 스킨케어 단어가 같이 나오면 `관련`, 아니면 `확인필요` 로
> 표시만 하고 **버리지는 않습니다.** (놓치는 것보다 낫다고 판단)
> 아예 빼고 싶으면 Variables 에 `REDDIT_ONLY_RELEVANT=1` 을 넣으세요.

## 셋업

### 1) 레딧 API 앱 만들기 (무료, 5분)

1. 레딧에 로그인 후 <https://www.reddit.com/prefs/apps> 접속
2. 맨 아래 **create another app...** 클릭
3. 이렇게 입력합니다.
   - **name**: `dalba-monitor` (아무거나)
   - 타입: **script** 선택 ← 중요
   - **redirect uri**: `http://localhost:8080` (안 쓰지만 필수 입력값)
4. 만들고 나면
   - 앱 이름 **바로 아래 문자열** = `REDDIT_CLIENT_ID`
   - **secret** 항목 = `REDDIT_CLIENT_SECRET`

공식 API 라 무료이고 차단당하지 않습니다. (분당 100회 제한은 코드에서 지킵니다)

### 2) 구글 시트 준비

기존 `scraper.py` / 인스타 수집기와 **같은 서비스계정 JSON**(`GOOGLE_CREDENTIALS`)을 씁니다.
결과를 받을 스프레드시트를 하나 만들고, **서비스계정 이메일과 편집자(Editor)로 공유**한 뒤
주소창의 시트 ID(`/d/` 와 `/edit` 사이 문자열)를 `REDDIT_SHEET_ID` 로 등록하세요.

> 시트 설정을 생략해도 동작합니다. 이 경우 결과는 CSV 로만 저장되고
> Actions 실행 결과 페이지 하단 **Artifacts** 에서 내려받을 수 있습니다.

### 3) GitHub 에 등록

**Settings → Secrets and variables → Actions**

Secrets 탭:

| 이름 | 필수 | 설명 |
| --- | --- | --- |
| `REDDIT_CLIENT_ID` | ✅ | 레딧 앱 client id |
| `REDDIT_CLIENT_SECRET` | ✅ | 레딧 앱 secret |
| `GOOGLE_CREDENTIALS` | 시트 쓸 때 | 구글 서비스계정 JSON (기존과 동일) |
| `REDDIT_USERNAME` / `REDDIT_PASSWORD` | ❌ | 계정 인증이 필요할 때만. 2단계인증 계정은 사용 불가 |

Variables 탭 (선택, 기본값을 바꾸고 싶을 때만):

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `REDDIT_SHEET_ID` | (없음) | 결과를 쓸 스프레드시트 ID |
| `REDDIT_OUTPUT_TAB` | `레딧언급` | 결과 탭 이름 |
| `REDDIT_QUERIES` | `dalba, d'alba, dalba white truffle, 달바` | 검색어(쉼표 구분) |
| `REDDIT_TIME_FILTER` | `week` | 검색 기간 `hour`/`day`/`week`/`month` |
| `REDDIT_SCAN_SUBREDDITS` | 뷰티 서브레딧 9개 | 댓글을 훑을 서브레딧. `none` 이면 끔 |
| `REDDIT_MAX_SEARCH_PAGES` | `3` | 검색어당 최대 페이지 (100건/장) |
| `REDDIT_MAX_COMMENT_PAGES` | `20` | 서브레딧당 최대 댓글 페이지 (100건/장) |
| `REDDIT_TOP_COMMENTS_PER_POST` | `3` | 언급 글마다 같이 담을 반응 댓글 수 |
| `REDDIT_MAX_ROWS` | `5000` | 시트에 유지할 최대 행 수 |
| `REDDIT_ONLY_RELEVANT` | `0` | `1` 이면 `확인필요` 는 저장 안 함 |

## 실행

- **자동**: 매일 한국시간 **오전 9시** (`.github/workflows/reddit-dalba-monitor.yml`)
- **수동**: Actions 탭 → *Reddit Dalba Monitor* → **Run workflow**
- **로컬 테스트**:
  ```bash
  cd reddit-dalba-monitor
  pip install -r requirements.txt
  export REDDIT_CLIENT_ID='...'
  export REDDIT_CLIENT_SECRET='...'
  # 시트 없이 CSV 만 보고 싶으면 아래 두 줄 생략
  export GOOGLE_CREDENTIALS="$(cat service_account.json)"
  export SHEET_ID='...'
  python reddit_dalba_monitor.py
  ```

## 참고

- 한 번 실행에 API 호출은 대략 **200~300회**, 시간은 **4~6분** 정도 걸립니다.
  (분당 100회 제한을 지키느라 호출 사이에 1.1초씩 쉽니다)
- 레딧 공식 API 는 **댓글 전문 검색을 지원하지 않습니다.** 그래서 3번 경로처럼
  서브레딧 최신 댓글을 훑는 방식을 씁니다. 감시할 서브레딧을 늘리고 싶으면
  `REDDIT_SCAN_SUBREDDITS` 에 추가하세요 (많아질수록 실행 시간도 늘어납니다).
- 삭제된 글/댓글은 다시 가져오지 않지만, 이미 시트에 담긴 내용은 그대로 남습니다.
