"""교안에서 긁어 온 한국어 문구를 사람이 읽는 문장으로 갈아 끼운다.

교안 PPT 칸에서 뽑아낸 글은 체언으로 끝나거나 한 문장이 여러 줄로 쪼개져
있어 그대로 화면에 걸면 읽히지 않는다. rewrites/ 에 제품별로 고쳐 쓴 문장을
두고, 여기서 web/data/products.json 에 덮어쓴다.

고치는 자리
  포지셔닝.문구   목록 카드의 한 줄 소개
  특징            제품 화면의 '제품 특징'
  스펙.용량       나라마다 파는 용량이 다른 제품이 있다 (미국은 프로2X 100ml만)

영어는 이미 사람이 다시 쓴 글이라 건드리지 않는다. 수치와 성분 이름은
교안 원문 그대로 두고 문장만 다듬었다.

여러 번 돌려도 결과가 같다. rewrites/ 를 고치고 다시 돌리면 된다.

사용: python rewrite.py [--check]
"""

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "web", "data", "products.json")
DIR = os.path.join(HERE, "rewrites")


def 모으기():
    """rewrites/ 의 조각을 한 표로 합친다. 파일이 나뉜 건 사람이 보기 좋자는 것뿐이다."""
    표 = {}
    for path in sorted(glob.glob(os.path.join(DIR, "*.json"))):
        d = json.load(open(path, encoding="utf-8"))
        겹침 = set(표) & set(d.get("제품", {}))
        if 겹침:
            sys.exit(f"{os.path.basename(path)} 에 이미 있는 제품이 또 있다: {겹침}")
        표.update(d.get("제품", {}))
    return 표


def 적용(p, 새것):
    """제품 하나에 고쳐 쓴 글을 덮어쓴다."""
    바뀐 = []
    if "포지셔닝" in 새것:
        p.setdefault("포지셔닝", {"문구": "", "태그": []})
        if p["포지셔닝"] is None:
            p["포지셔닝"] = {"문구": "", "태그": []}
        if p["포지셔닝"].get("문구") != 새것["포지셔닝"]:
            p["포지셔닝"]["문구"] = 새것["포지셔닝"]
            바뀐.append("포지셔닝")
    if "특징" in 새것:
        특징 = [{"제목": f["제목"], "설명": list(f.get("설명", []))} for f in 새것["특징"]]
        if p.get("특징") != 특징:
            p["특징"] = 특징
            바뀐.append("특징")
    if "스펙" in 새것:
        for k, v in 새것["스펙"].items():
            if p["스펙"].get(k) != v:
                p["스펙"][k] = v
                바뀐.append(f"스펙.{k}")
            # 영어 화면도 같은 용량을 봐야 한다.
            en = p.setdefault("en판", {}).setdefault("스펙", {})
            if en.get(k) and en[k] != v:
                en[k] = v
                바뀐.append(f"en판.스펙.{k}")
    return 바뀐


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="덮어쓰지 않고 달라지는 자리만 알려준다")
    a = ap.parse_args()

    표 = 모으기()
    products = json.load(open(OUT, encoding="utf-8"))
    있는것 = {p["slug"] for p in products}
    모르는 = set(표) - 있는것
    if 모르는:
        sys.exit(f"products.json 에 없는 슬러그: {', '.join(sorted(모르는))}")

    손댄것, 안쓴것 = [], sorted(있는것 - set(표))
    for p in products:
        새것 = 표.get(p["slug"])
        if not 새것:
            continue
        바뀐 = 적용(p, 새것)
        if 바뀐:
            손댄것.append((p["slug"], 바뀐))

    if not a.check:
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=1)
            f.write("\n")

    print(f"고쳐 쓴 제품 {len(표)}개 중 {len(손댄것)}개가 바뀌었다"
          f"{' (확인만 했다)' if a.check else ''}.")
    for slug, 바뀐 in 손댄것:
        print(f"  {slug[:46]:<48} {', '.join(바뀐)}")
    if 안쓴것:
        print(f"\n아직 고쳐 쓰지 않은 제품 {len(안쓴것)}개:")
        for s in 안쓴것:
            print(f"  - {s}")


if __name__ == "__main__":
    main()
