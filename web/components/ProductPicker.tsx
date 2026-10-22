"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useLang, useT } from "@/components/Lang";
import TopSellers from "@/components/TopSellers";
import Notice, { type NoticeItem } from "@/components/Notice";
// 값을 가져오면 제품 데이터 전체가 클라이언트 번들에 딸려 온다. 타입만 가져오고
// 실제 값은 서버에서 props 로 받는다.
import type { Line, ProductCard, SetItem, TopItem } from "@/lib/products";

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

/** 제품 카드 한 장. 라인별 목록과 검색 결과가 같이 쓴다. */
function Card({ c }: { c: ProductCard }) {
  const t = useT();
  const { lang } = useLang();
  return (
    <li>
      <Link className="pw-card" href={`/products/${c.slug}`}>
        <div className="pw-thumb">
          {c.대표이미지 ? (
            // 원본 이미지 크기가 제각각이다. 채우지 않고 맞춰 넣는다.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={c.대표이미지} alt="" loading="lazy" />
          ) : (
            <span className="pw-thumb-none">
              {t("이미지 없음", "No image")}
            </span>
          )}
        </div>
        <div className="pw-card-body">
          {/* 많이 팔린 10개 안에 드는 제품이면 목록에서도 알아보게 한다. */}
          {c.순위 && (
            <p className="pw-card-rank">
              {t(`판매 ${c.순위}위`, `#${c.순위} by sales`)}
            </p>
          )}
          <h2>{t(c.ko, c.en)}</h2>
          {/* 영어 화면에서는 제목이 이미 영어다. 같은 이름을 두 번 쓰지 않는다. */}
          {lang === "ko" && c.en && <p className="pw-en">{c.en}</p>}
          {t(c.한줄, c.한줄En) && (
            <p className="pw-line">{t(c.한줄, c.한줄En)}</p>
          )}
          <p className="pw-meta">
            {t(c.용량, c.용량En)}
            {t(c.기능성, c.기능성En) ? ` · ${t(c.기능성, c.기능성En)}` : ""}
          </p>
        </div>
      </Link>
    </li>
  );
}

/** 세트 카드 한 장. 교안이 없어 이름과 제품컷만 보여준다. */
function SetCard({ s }: { s: SetItem }) {
  const t = useT();
  const { lang } = useLang();
  return (
    <li>
      <Link className="pw-card" href={`/sets/${s.pid}`}>
        <div className="pw-thumb">
          {s.이미지 ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={s.이미지} alt="" loading="lazy" />
          ) : (
            <span className="pw-thumb-none">{t("이미지 없음", "No image")}</span>
          )}
        </div>
        <div className="pw-card-body">
          <h2>{t(s.ko, s.en)}</h2>
          {lang === "ko" && s.en && <p className="pw-en">{s.en}</p>}
          <p className="pw-meta">{s.pid}</p>
        </div>
      </Link>
    </li>
  );
}

/** 세트는 이름과 번호로만 찾는다. */
function setMatches(s: SetItem, q: string) {
  if (!q) return true;
  const hay = `${s.ko} ${s.en} ${s.pid}`.toLowerCase();
  return hay.includes(q) || hay.replace(/\s+/g, "").includes(q.replace(/\s+/g, ""));
}

type 묶음 = "단품" | "세트";

export default function ProductPicker({
  cards,
  top,
  live,
  period,
  liveInfo,
  lines,
  notice,
  noticeCsv,
  sets,
}: {
  cards: ProductCard[];
  top: TopItem[];
  live: TopItem[];
  period: { ko: string; en: string };
  liveInfo: { 합산: boolean; 기간: { ko: string; en: string } };
  lines: Line[];
  notice: NoticeItem[];
  noticeCsv: string;
  sets: SetItem[];
}) {
  const [q, setQ] = useState("");
  const [묶음, set묶음] = useState<묶음>("단품");
  const t = useT();
  const 세트보기 = 묶음 === "세트";

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return cards.filter((c) => matches(c, needle));
  }, [cards, q]);

  const shownSets = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return sets.filter((s) => setMatches(s, needle));
  }, [sets, q]);

  return (
    <main className="pw-main">
      {/* 머리말은 없앴다. 화면 맨 위 제목과 겹쳐 한 줄만 더 차지했다.
          대신 많이 팔린 10개가 이 화면의 첫 제목이 된다. */}
      {/* 공지는 늘 맨 위다. 사장님이 시트에 쓰면 배포 없이 바뀐다. */}
      <Notice csv={noticeCsv} baked={notice} />

      <TopSellers items={top} live={live} period={period} liveInfo={liveInfo} />

      {/* 단품은 교안이 있고, 세트는 샵 그림만 있다. 그래서 목록을 나눠 둔다. */}
      <div className="pw-basis pw-kind" role="group" aria-label={t("무엇을 볼지", "What to show")}>
        {(["단품", "세트"] as 묶음[]).map((k) => (
          <button
            key={k}
            type="button"
            aria-pressed={묶음 === k}
            onClick={() => set묶음(k)}
          >
            {k === "단품"
              ? t(`단품 ${cards.length}`, `Products ${cards.length}`)
              : t(`세트 ${sets.length}`, `Bundles ${sets.length}`)}
          </button>
        ))}
      </div>

      <p className="pw-intro">
        {세트보기
          ? t(
              `지금 US 틱톡샵에서 파는 세트 ${sets.length}개입니다. 세트는 단품 교안이 없어, 누르면 판매 페이지의 제품컷과 상세페이지를 그대로 보여줍니다.`,
              `${sets.length} bundles on the US shop right now. Bundles have no product guide, so opening one shows the listing's own images.`,
            )
          : t(
              `제품 ${cards.length}개입니다. 제품을 누르면 브리프와 이미지, 제품 특징, 그리고 성분·향·사용법 이야기를 볼 수 있습니다.`,
              `${cards.length} products. Open one for the brief, the images, the feature list, and the longer notes on ingredients, scent and how it's used.`,
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
          {세트보기
            ? q.trim()
              ? `${shownSets.length} / ${sets.length}`
              : t(`${sets.length}개`, `${sets.length}`)
            : q.trim()
              ? `${shown.length} / ${cards.length}`
              : t(`${cards.length}개`, `${cards.length}`)}
        </span>
      </div>

      {세트보기 ? (
        shownSets.length === 0 ? (
          <p className="pw-none">
            {t(`“${q}” 와 맞는 세트가 없습니다.`, `No bundle matches “${q}”.`)}
          </p>
        ) : (
          <ul className="pw-grid">
            {shownSets.map((s) => (
              <SetCard key={s.pid} s={s} />
            ))}
          </ul>
        )
      ) : shown.length === 0 ? (
        <p className="pw-none">
          {t(`“${q}” 와 맞는 제품이 없습니다.`, `Nothing matches “${q}”.`)}
        </p>
      ) : q.trim() ? (
        // 찾는 중에는 라인을 나누지 않는다. 걸린 것만 한 줄로 보여준다.
        <ul className="pw-grid">
          {shown.map((c) => (
            <Card key={c.slug} c={c} />
          ))}
        </ul>
      ) : (
        lines.map((ln) => {
          const 속한것 = shown.filter((c) => c.라인 === ln.키);
          if (!속한것.length) return null;
          return (
            <section className="pw-group" key={ln.키}>
              <h2>
                {t(ln.ko, ln.en)}
                <span className="pw-group-n">{속한것.length}</span>
              </h2>
              <p className="pw-note">{t(ln.설명ko, ln.설명en)}</p>
              <ul className="pw-grid">
                {속한것.map((c) => (
                  <Card key={c.slug} c={c} />
                ))}
              </ul>
            </section>
          );
        })
      )}
    </main>
  );
}
