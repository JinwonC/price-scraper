"""딜 가격표에 걸 제품컷을 받는다. web/public/deal/<pid>.jpg.

상위 10개용으로 web/public/top 에 이미 받아 둔 제품은 건너뛴다 — 화면이
그쪽을 먼저 본다. 받는 방법은 product-edu/shop_images.py 와 같아서 그
함수를 그대로 쓴다(틱톡샵 상품 페이지의 og:image).

받고 나면 deal.py 를 다시 돌려 '이미지' 칸을 채우면 된다.

사용:
  python deal_images.py [pid ...]    인자가 없으면 아직 없는 것만 받는다
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "product-edu"))
from shop_images import fetch_one  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "..", "web")
NAMES = os.path.join(HERE, "names.json")
IMG_DIR = os.path.join(WEB, "public", "deal")
TOP_DIR = os.path.join(WEB, "public", "top")


def main():
    pids = sys.argv[1:] or list(json.load(open(NAMES, encoding="utf-8"))["제품"])
    os.makedirs(IMG_DIR, exist_ok=True)

    실패 = []
    for i, pid in enumerate(pids, 1):
        있는곳 = next((d for d in (TOP_DIR, IMG_DIR)
                     if os.path.exists(os.path.join(d, f"{pid}.jpg"))), None)
        if 있는곳 and not sys.argv[1:]:
            print(f"  {i:>2}/{len(pids)} {pid} 이미 있음")
            continue
        try:
            난 = fetch_one(pid, os.path.join(IMG_DIR, f"{pid}.jpg"))
            print(f"  {i:>2}/{len(pids)} {pid} {난}")
        except Exception as e:
            print(f"  {i:>2}/{len(pids)} {pid} 실패 — {e}")
            실패.append(pid)
        time.sleep(1.6)  # 몰아치면 막힌다

    있음 = sum(1 for p in pids
              if any(os.path.exists(os.path.join(d, f"{p}.jpg"))
                     for d in (TOP_DIR, IMG_DIR)))
    print(f"\n제품컷 {있음}/{len(pids)} 개.")
    for p in 실패:
        print(f"  못 받음: {p}")
    if 실패:
        print("  다시 돌리거나, 셀러센터에서 받아 web/public/deal/<pid>.jpg 로 넣으면 된다.")


if __name__ == "__main__":
    main()
