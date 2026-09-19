"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ProductCard } from "@/lib/products";

/** 검색어를 제품명·영문명·태그·한 줄 소개에 두루 맞춰 본다. */
function matches(card: ProductCard, q: string): boolean {
  if (!q) return true;
  const hay = [card.ko, card.en, card.한줄, card.태그.join(" "), card.용량가격]
    .join(" ")
    .toLowerCase();
  // 띄어쓰기를 무시하고도 걸리게 한다("리턴오일" 로도 찾아지도록)
  return hay.includes(q) || hay.replace(/\s+/g, "").includes(q.replace(/\s+/g, ""));
}

export default function ProductPicker({ cards }: { cards: ProductCard[] }) {
  const [q, setQ] = useState("");

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return cards.filter((c) => matches(c, needle));
  }, [cards, q]);

  return (
    <>
      <div className="pw-search">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="제품 이름으로 찾기 (예: 클렌저, spray, 선스크린)"
          aria-label="제품 검색"
        />
        <span className="pw-count">
          {q.trim() ? `${shown.length} / ${cards.length}개` : `${cards.length}개`}
        </span>
      </div>

      {shown.length === 0 ? (
        <p className="pw-none">
          “{q}” 와 맞는 제품이 없습니다. 교안이 없는 제품일 수도 있습니다.
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
                    <span className="pw-thumb-none">이미지 없음</span>
                  )}
                </div>
                <div className="pw-card-body">
                  <h2>{c.ko}</h2>
                  <p className="pw-en">{c.en}</p>
                  {c.한줄 && <p className="pw-line">{c.한줄}</p>}
                  <p className="pw-meta">
                    {c.용량가격 || "용량·가격 교안에 없음"}
                    {c.기능성 ? ` · ${c.기능성}` : ""}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
