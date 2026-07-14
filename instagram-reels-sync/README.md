# 인스타그램 릴스 아웃라이어 수집기 (Apify → 구글 시트)

구글 시트의 인스타그램 핸들 목록을 읽어, 각 계정의 **최근 30일 릴스**를 수집하고
계정별 **평균 조회수 대비 배수**를 계산해 "평소보다 잘 나온 영상"을 찾아 시트에 정리합니다.

## 동작 방식

1. 대상 스프레드시트의 `시트1` 탭 **A열**에서 인스타그램 핸들을 읽습니다.
   (헤더 `Instagram handle` 행과 빈 칸, 앞의 `@` 는 자동으로 정리)
2. Apify [`apify/instagram-scraper`](https://apify.com/apify/instagram-scraper) 액터를
   **한 번의 run** 으로 모든 핸들에 대해 실행합니다. (`onlyPostsNewerThan: "30 days"`)
3. 수집된 게시물 중 **릴스만** 골라 계정별로 묶고, 다음을 계산합니다.
   - `평균조회수` = 계정의 최근 30일 릴스 평균 조회수
   - `배수` = 릴스 조회수 ÷ 평균조회수  → 배수가 클수록 아웃라이어
4. 결과를 같은 스프레드시트의 두 탭에 저장합니다.
   - **릴스분석**: 릴스 단위 상세 (조회수 / 평균 / 배수 / 좋아요 / 댓글 / 게시일 / 캡션),
     배수 내림차순 정렬, `배수 ≥ 기준`이면 `★` 표시
   - **릴스요약**: 계정 단위 요약 (릴스수 / 평균 / 최고 조회수 / 최고 릴스 URL / 상태)

## 셋업

### 1) Apify 토큰

Apify 콘솔 → **Settings → Integrations → API tokens** 에서 토큰을 복사합니다.
(이전에 사용한 계정 그대로 사용하시면 됩니다.)

### 2) 구글 서비스계정

기존 `scraper.py` 와 동일한 서비스계정 JSON(`GOOGLE_CREDENTIALS`)을 사용합니다.
**대상 스프레드시트를 서비스계정 이메일과 편집자(Editor)로 공유**해야 합니다.
(서비스계정 이메일은 JSON 의 `client_email` 값)

### 3) GitHub Secrets 등록

리포지토리 **Settings → Secrets and variables → Actions** 에 등록합니다.

| 이름 | 종류 | 설명 |
| --- | --- | --- |
| `APIFY_TOKEN` | Secret | Apify API 토큰 (필수) |
| `GOOGLE_CREDENTIALS` | Secret | 구글 서비스계정 JSON (필수, 기존과 동일) |

선택값(Variables, 기본값을 바꾸고 싶을 때만):

| 이름 | 기본값 | 설명 |
| --- | --- | --- |
| `IG_SHEET_ID` | 코드에 내장된 대상 시트 | 다른 스프레드시트를 쓸 때 |
| `IG_INPUT_TAB` | `시트1` | 핸들이 있는 탭 |
| `IG_OUTPUT_TAB` | `릴스분석` | 릴스 상세 결과 탭 |
| `IG_SUMMARY_TAB` | `릴스요약` | 계정 요약 탭 |
| `IG_DAYS` | `30` | 최근 며칠을 볼지 |
| `IG_RESULTS_LIMIT` | `100` | 계정당 최대 수집 게시물 수 |
| `IG_OUTPERFORM_RATIO` | `2.0` | `★` 로 표시할 배수 기준 |

## 실행

- **자동**: GitHub Actions 에서 매일 실행 (`.github/workflows/instagram-reels-sync.yml`).
- **수동**: Actions 탭 → *Instagram Reels Sync* → **Run workflow**.
- **로컬 테스트**:
  ```bash
  cd instagram-reels-sync
  pip install -r requirements.txt
  export APIFY_TOKEN='...'
  export GOOGLE_CREDENTIALS="$(cat service_account.json)"
  python instagram_reels_sync.py
  ```

## 참고

- Apify 액터는 유료 사용량이 발생할 수 있습니다. 계정 수 × 게시물 수에 비례하니
  `IG_RESULTS_LIMIT` 로 조절하세요.
- 인스타그램 조회수(Play count)는 **릴스(동영상)** 에만 존재합니다. 사진/캐러셀 게시물은
  집계에서 제외됩니다.
- 비공개 계정, 존재하지 않는 핸들, 최근 릴스가 없는 계정은 `릴스요약` 의 `상태` 열에
  `데이터 없음` 으로 표시됩니다.
