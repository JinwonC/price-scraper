# BFCM 딜 가격표

사이트의 **BFCM 할인율** 탭(`/deals`)에 쓰는 자료를 만든다. 정가·딜가·할인율은
틱톡샵 셀러센터에서 뽑아 둔 구글 시트에서 가져오고, 제품 차례는 최근 7일
**라이브 매출**이 큰 순이다.

시트: `1p9HmIOGnc5gE8kQILFT3T_8NAuKMRc-RkY2cs_gQu0M`
- `Deal Price` 탭 — pid · 리스팅 이름 · SKU 이름 · 정가 · 딜가 · 할인율
- `PID별 7일 매출` 탭 — pid · LIVE GMV 등

**매출액은 싣지 않는다.** 이 저장소는 공개다. 라이브 매출은 차례를 매기는 데만
쓰고 결과 파일에는 들어가지 않는다. 샵에 걸린 정가·딜가·할인율은 누구나 보는
값이라 그대로 싣는다.

## 하는 법

1. 시트 두 탭을 읽어 스크래치패드에 탭으로 나뉜 파일 두 개로 적는다.

   `sku.tsv` — `pid⇥SKU 이름⇥정가⇥딜가⇥할인율`
   ```
   1732689334754448092	Default	79.99	25.99	67.5
   ```

   `live.tsv` — `pid⇥LIVE GMV`
   ```
   1732689334754448092	3345.49
   ```

2. 가격표를 굽는다.
   ```
   python deal.py <sku.tsv> <live.tsv>
   ```
   → `web/data/deal-prices.json`

   이름표에 없는 pid 가 있으면 그 번호를 찍어 준다. `names.json` 의 `제품` 에
   짧은 한국어·영어 이름과 태그(`라이브`·`틱톡`·`신상`·`할인`)를 적고 다시
   돌리면 된다. 시트의 리스팅 이름은 길어서 카드에 그대로 넣을 수 없다.

3. 제품컷이 빠진 제품이 있으면 받는다.
   ```
   python deal_images.py          # 아직 없는 것만
   python deal_images.py <pid>    # 특정 제품만 다시
   ```
   → `web/public/deal/<pid>.jpg` (440px). 상위 10개용으로 `web/public/top` 에
   이미 받아 둔 제품은 건드리지 않는다 — 화면이 그쪽을 먼저 본다.
   받은 뒤 2번을 다시 돌려야 `이미지` 칸이 채워진다.

   시스템 Pillow 가 깨져 있으면 `PYTHONPATH=/tmp/pylibs` 를 앞에 붙인다.

4. `cd web && npm run build` 로 확인하고 커밋한다.
