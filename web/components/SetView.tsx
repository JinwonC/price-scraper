"use client";

import Link from "next/link";
import { useT } from "@/components/Lang";
import ShopLink from "@/components/ShopLink";
import ShopGallery, { type Shot } from "@/components/ShopGallery";
import type { SetItem } from "@/lib/products";

/**
 * 세트 화면.
 *
 * 세트·번들은 교안이 없다. 크리에이터에게 필요한 건 어차피 '무엇이 들어 있고
 * 어떻게 생겼는지' 와 제품 번호라, 샵에 걸린 제품컷과 상세페이지 컷을 그대로
 * 보여주고 번호와 판매 페이지 링크를 붙인다.
 */
export default function SetView({
  item,
  shop,
}: {
  item: SetItem;
  shop: { 갤러리: Shot[]; 상세: Shot[] };
}) {
  const t = useT();

  return (
    <main className="pw-main">
      <Link className="pw-back" href="/products">
        {t("← 제품 목록", "← All products")}
      </Link>

      <header className="pw-head">
        <h1 className="pw-h1">{t(item.ko, item.en)}</h1>
        {/* 영어 화면에서는 제목이 이미 영어다. 같은 이름을 두 번 쓰지 않는다. */}
        <p className="pw-shop-row">
          <ShopLink pid={item.pid} />
        </p>
      </header>

      <p className="pw-note pw-set-note">
        {t(
          "세트 구성은 단품 교안이 없습니다. 아래는 실제 판매 페이지에 걸려 있는 그림 그대로입니다 — 구성품과 수량도 여기서 확인하세요.",
          "Bundles have no product guide of their own. Below is exactly what's on the live listing — check the contents and quantities there.",
        )}
      </p>

      <ShopGallery 갤러리={shop.갤러리} 상세={shop.상세} />
    </main>
  );
}
