"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useT } from "@/components/Lang";
import type { ProductCard } from "@/lib/products";

/** 검색어를 제품명·영문명·태그·한 줄 소개에 두루 맞춰 본다. */
function matches(card: ProductCard, q: string): boolean {
  if (!q) return true;
  const hay = [
    card.ko,
    card.en,
    card.한줄,
    card.한줄En,
    card.태그.join(" "),
    card.용량,
  ]
    .join(" ")
    .toLowerCase();
  // 띄어쓰기를 무시하고도 걸리게 한다("리턴오일" 로도 찾아지도록)
  return hay.includes(q) || hay.replace(/\s+/g, "").includes(q.replace(/\s+/g, ""));
}

export default function ProductPicker({ cards }: { cards: ProductCard[] }) {
  const [q, setQ] = useState("");
  const t = useT();

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return cards.filter((c) => matches(c, needle));
  }, [cards, q]);

  return (
    <main className="pw-main">
      <h1 className="pw-h1">{t("제품을 고르세요", "Pick a product")}</h1>
      <p className="pw-intro">
        {t(
          `사내 제품 교안 ${cards.length}개를 정리한 것입니다. 제품을 누르면 브리프와 이미지, 제품 특징, 그리고 성분·향·사용법 이야기를 볼 수 있습니다.`,
          `${cards.length} products, pulled from d'Alba's internal training decks. Open one for the brief, the images, the feature list, and the longer notes on ingredients, scent and how it's used.`,
        )}
      </p>

      <div className="pw-search">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t(
            "제품 이름으로 찾기 (예: 클렌저, spray, 선스크린)",
            "Search by name (e.g. cleanser, serum, sunscreen)",
          )}
          aria-label={t("제품 검색", "Search products")}
        />
        <span className="pw-count">
          {q.trim()
            ? `${shown.length} / ${cards.length}`
            : t(`${cards.length}개`, `${cards.length}`)}
        </span>
      </div>

      {shown.length === 0 ? (
        <p className="pw-none">
          {t(
            `“${q}” 와 맞는 제품이 없습니다. 교안이 없는 제품일 수도 있습니다.`,
            `Nothing matches “${q}”. There may be no deck for that product.`,
          )}
        </p>
      ) : (
        <ul className="pw-grid">
          {shown.map((c) => (
            <li key={c.slug}>
              <Link className="pw-card" href={`/products/${c.slug}`}>
                <div className="pw-thumb">
                  {c.대표이미지 ? (
                    // 교안에서 꺼낸 이미지라 크기가 제각각이다. 채우지 않고 맞춰 넣는다.
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.대표이미지} alt="" loading="lazy" />
                  ) : (
                    <span className="pw-thumb-none">
                      {t("이미지 없음", "No image")}
                    </span>
                  )}
                </div>
                <div className="pw-card-body">
                  <h2>{t(c.ko, c.en)}</h2>
                  {t(c.en, "") && <p className="pw-en">{t(c.en, "")}</p>}
                  {t(c.한줄, c.한줄En) && (
                    <p className="pw-line">{t(c.한줄, c.한줄En)}</p>
                  )}
                  <p className="pw-meta">
                    {t(c.용량, c.용량En) || t("용량 교안에 없음", "size not in deck")}
                    {t(c.기능성, c.기능성En) ? ` · ${t(c.기능성, c.기능성En)}` : ""}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
