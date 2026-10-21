# 제품 교안 → 웹사이트

구글 드라이브의 제품 교안(PPTX)을 읽어 `web/` 의 제품 페이지 데이터를 만든다.
결과물은 `/products` 에서 제품별로 볼 수 있다.

## 왜 이렇게 만들었나

- 커넥터의 **파일 다운로드는 base64 로 대화창에 들어온다.** 교안은 5~313MB 라 그 경로로는
  못 쓴다. 그래서 공개 링크로 **디스크에 바로 받는다**(`fetch.py`).
- 교안 텍스트만으로는 부족하다. **시험 수치가 이미지 안에만 있는 슬라이드**가 있다
  (리턴 오일 크림 클렌저의 TEST 01~06 이 대표적). 그래서 "글자가 거의 없는데 이미지가
  있는 슬라이드"를 자동으로 골라내고, 그 이미지는 사람이 읽어서 `image-reads.json` 에 적는다.
- `python-pptx` 는 **그룹으로 묶인 도형 안의 글자를 놓친다.** `extract.py` 의 `walk()` 가
  그룹을 재귀로 펼친다. 이걸 안 하면 클렌저 교안에서만 17블록이 통째로 빠진다.

## 개인정보 주의

여러 교안의 **「기능성화장품 심사 제외 품목 보고서」 이미지에 신청인 성명과
주민등록번호란의 생년월일이 찍혀 있다.** 이 이미지들은 절대 웹에 올리지 않는다.
필요한 값(pH, 고시 원료, 심사번호, 보고완료일)만 `image-reads.json` 에 텍스트로 옮긴다.
`picks.json` 은 사람이 눈으로 확인하고 고른 목록이다 — **자동 선별하지 않는다.**

## 실행 순서

```bash
pip install -r requirements.txt

# 0) 드라이브 교안 폴더를 "링크가 있는 모든 사용자 · 뷰어" 로 잠시 바꾼다.
#    (끝나면 반드시 되돌릴 것. 미출시 제품 교안이 포함돼 있다.)

python fetch.py            # 드라이브 → pptx/ 내려받고 텍스트 추출 → decks.json
                           #   글자 없는 슬라이드의 이미지는 images/ 로 따로 빠진다
python sheets.py           # 제품별 이미지 후보 시트 → sheets/  (사람이 눈으로 고른다)
                           #   고른 결과를 picks.json 에 적는다
python build_products.py   # decks.json + image-reads.json → products.json
python publish.py          # 검열 그물을 통과시켜 ../web/data/products.json 으로
python rewrite.py          # rewrites/ 의 고쳐 쓴 한국어 문장을 덮어쓴다
```

## 사진은 교안 것을 쓰지 않는다

사이트에 거는 사진은 전부 **틱톡샵 상품 페이지에서 받은 것**이다. 크리에이터가
방송에 쓸 그림은 실제 판매 페이지와 같아야 손님이 보는 것과 어긋나지 않는다.
교안에서 골라 내보내던 사진(`picks.json`, `export_images.py`, `sheets.py`)은
더 이상 사이트로 나가지 않는다 — 교안 작업 기록으로만 남겨 둔다.

```bash
python shop_gallery.py --out /tmp/shop-images   # 갤러리 + 상세컷, 원본 해상도
python shop_web_images.py --src /tmp/shop-images  # 긴 변 900px WebP → web/public/shop
```

원본은 한 제품에 30MB 가까이 돼 저장소에 넣지 않는다. 줄인 것만 커밋한다.

## 한국어 문장은 따로 고쳐 쓴다

교안 PPT 칸에서 뽑아낸 글은 체언으로 끝나거나 한 문장이 여러 줄로 쪼개져 있어
그대로 걸면 읽히지 않는다. `rewrites/` 에 제품별로 고쳐 쓴 문장을 두고
`rewrite.py` 가 `web/data/products.json` 에 덮어쓴다. 수치와 성분 이름은 교안
원문 그대로 두고 문장만 다듬는다. 영어는 이미 사람이 다시 쓴 글이라 건드리지
않는다.

`manifest.json` 은 제품별 **현행 교안 파일 1개씩**의 드라이브 ID 다.
드라이브에는 같은 교안의 구버전이 많아서(리턴 오일 크림 클렌저만 6개) 자동으로 고르지
않고 여기에 적어 둔다. 교안이 갱신되면 이 파일의 ID 를 바꾼다.

## 파일

| 파일 | 하는 일 |
| --- | --- |
| `manifest.json` | 제품별 현행 교안의 드라이브 파일 ID |
| `matching.json` | 영문 제품명 ↔ 한국어 교안 매칭 (확인 완료본) |
| `fetch.py` | 다운로드 + 텍스트 추출 + 글자 없는 슬라이드 이미지 추출 |
| `extract.py` | PPTX 한 개 → 구조화 JSON (그룹 도형까지 훑는다) |
| `sheets.py` | 제품별 이미지 후보 검수 시트 생성 |
| `picks.json` | 웹에 쓸 이미지로 고른 목록 + 제외 원칙 |
| `image-reads.json` | 이미지에서 읽어낸 수치·문서 내용 |
| `build_products.py` | 최종 `products.json` 생성 |
| `export_images.py` | (더 이상 쓰지 않음) 교안 이미지 내보내기 |
| `shop_gallery.py` | 틱톡샵 상품 페이지의 갤러리·상세컷 원본 받기 |
| `shop_web_images.py` | 받은 사진을 사이트 크기로 줄여 web/public/shop 으로 |
| `rewrites/` · `rewrite.py` | 교안 문구를 고쳐 쓴 한국어 문장과 적용기 |
| `shop-shots.json` | 제품별 틱톡샵 pid + 공식 컷이 대신한 교안 픽 번호 |
| `shop_images.py` | 틱톡샵 공식 제품컷 받기 (교안 `00.jpg`, 상위 10개 썸네일) |
| `top_ranks.py` | CRUVA CSV → `web/data/top10.json` (많이 팔린 10개) |
| `publish.py` | 검열 그물을 통과시켜 web/data 로 내보내기 |

## 많이 팔린 10개 갱신하기

제품 목록 맨 위의 순위는 **자동으로 갱신되지 않는다.** CRUVA 는 MCP 도구라
스크립트가 바로 부를 수 없어서, 사람이(또는 클로드가) 주기적으로 돌려 줘야 한다.
30일 창이라 2~3주만 지나도 1위가 바뀐다.

```
# 1) CRUVA 에서 최근 30일 제품 성과를 CSV 로 받는다
#    search_brand_products(shop_id=…, timeseries=True,
#      date_from=…, date_to=오늘, as_csv=True,
#      columns=["product_id","product_name","total_gmv","live_gmv",
#               "affiliate_gmv","status"])
python top_ranks.py <받은.csv> --from 2026-09-10 --to 2026-10-10

# 2) 처음 보는 제품이 있으면 한국어 이름과 slug 를 손으로 채운다
#    (top_ranks.py 가 어느 제품인지 찍어 준다)

# 3) 제품컷을 받는다. 이미 있는 것은 건드리지 않는다
python shop_images.py
```

매출액은 싣지 않는다. 순위와 pid 만 올린다 — 이 저장소는 공개다.
