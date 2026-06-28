# 와썹맨 YouTube 스튜디오 → 구글 시트 자동 수집기

YouTube 채널의 **공개 통계**(구독자·조회수·좋아요)와 **스튜디오 분석 지표**
(시청시간·노출수·CTR·트래픽 등)를 매일 자동으로 구글 스프레드시트에 쌓아주는 도구입니다.

> 기존 `scraper.py`(가격 스크래퍼)와는 **완전히 별개**인 독립 프로젝트입니다.
> 이 폴더(`youtube-studio-sync/`) 안에서만 동작합니다.

## 동작 방식

OAuth 자격증명 **하나**로 아래 3가지를 모두 처리합니다.

| API | 용도 |
| --- | --- |
| YouTube Data API v3 | 채널/영상 공개 통계 |
| YouTube Analytics API | 스튜디오 분석 지표 (소유자 인증 필요) |
| Google Sheets / Drive | 새 스프레드시트 자동 생성 & 갱신 |

생성되는 시트 탭:

- **채널요약** — 매일 1행씩 누적 (날짜, 구독자, 총 조회수, 영상 수)
- **영상별통계** — 최근 영상별 조회수/좋아요/댓글 (매일 최신값으로 갱신)
- **스튜디오분석** — 일별 시청시간·노출수·CTR·구독 증감 등 (지연 데이터까지 백필)

---

## 셋업 (최초 1회)

### 1. Google Cloud 프로젝트 준비
1. https://console.cloud.google.com 에서 프로젝트 생성(또는 기존 것 사용)
2. **API 및 서비스 → 라이브러리**에서 아래 4개를 모두 "사용 설정":
   - YouTube Data API v3
   - YouTube Analytics API
   - Google Sheets API
   - Google Drive API

### 2. OAuth 동의 화면
1. **API 및 서비스 → OAuth 동의 화면** → 사용자 유형 **외부** 선택
2. 테스트 사용자에 **채널을 소유한 본인 구글 계정**을 추가
   (게시 안 해도 테스트 사용자면 동작합니다)

### 3. OAuth 클라이언트 생성
1. **사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID**
2. 애플리케이션 유형 **데스크톱 앱** 선택 후 생성
3. JSON 내려받아 이 폴더에 `client_secret.json` 으로 저장

### 4. 리프레시 토큰 발급 (본인 PC에서)
```bash
cd youtube-studio-sync
pip install -r requirements.txt
python get_refresh_token.py
```
브라우저가 열리면 **채널 소유 계정**으로 로그인/동의하세요.
터미널에 출력되는 3개 값을 복사해 둡니다.

### 5. GitHub Secrets 등록
저장소 **Settings → Secrets and variables → Actions → New repository secret** 에서:

| Secret 이름 | 값 |
| --- | --- |
| `GOOGLE_OAUTH_CLIENT_ID` | 4단계 출력값 |
| `GOOGLE_OAUTH_CLIENT_SECRET` | 4단계 출력값 |
| `GOOGLE_OAUTH_REFRESH_TOKEN` | 4단계 출력값 |

(선택) **Variables** 탭에서 추가 설정:

| Variable | 설명 |
| --- | --- |
| `SHEET_TITLE` | 시트 제목 변경 (기본: `와썹맨 YouTube 통계`) |
| `SHEET_ID` | 특정 시트에 고정하고 싶을 때 ID |
| `SHARE_EMAIL` | 새로 만든 시트를 공유할 이메일(편집권한) |

---

## 실행

- **자동**: 매일 한국시간 오전 10시(UTC 01:00)에 GitHub Actions가 실행
  (`.github/workflows/youtube-sync.yml`)
- **수동**: Actions 탭 → "YouTube Studio Sync" → **Run workflow**

### 로컬 테스트
```bash
cd youtube-studio-sync
export GOOGLE_OAUTH_CLIENT_ID=...
export GOOGLE_OAUTH_CLIENT_SECRET=...
export GOOGLE_OAUTH_REFRESH_TOKEN=...
python youtube_sync.py
```
실행 후 출력되는 시트 URL을 열면 데이터가 채워져 있습니다.

---

## 참고
- 스튜디오 분석 데이터는 확정까지 **2~3일 지연**이 있어, 스크립트가 최근 10일을
  거슬러 보며 빠진 날짜만 채워 넣습니다(중복 추가 없음).
- 수익(애드센스) 지표는 더 민감한 권한이 필요해 기본 포함하지 않았습니다.
  필요하면 `monetaryDimensions` 권한과 `estimatedRevenue` 지표를 추가하면 됩니다.
