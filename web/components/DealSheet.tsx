"use client";

import { useMemo, useState } from "react";
import { useT } from "@/components/Lang";
import Poster from "@/components/Poster";
import { shopUrl } from "@/components/ShopLink";
import type { DealItem, DealSummary } from "@/lib/deals";

/** 카드 머리 띠. 시트의 리스팅 머리말에서 갈라 둔 것이다. */
const 띠: Record<string, { ko: string; en: string }> = {
  라이브: { ko: "라이브 전용", en: "Live exclusive" },
  틱톡: { ko: "틱톡샵 전용", en: "TikTok exclusive" },
  신상: { ko: "신규", en: "New" },
  할인: { ko: "할인", en: "Flash sale" },
};
const 차례 = ["라이브", "틱톡", "신상", "할인"];

function 돈(n: number) {
  return `$${n.toFixed(2)}`;
}

/**
 * BFCM 딜 가격표.
 *
 * 크리에이터가 방송 전에 보는 화면이라, 눈에 먼저 들어와야 하는 것은 할인율과
 * 딜가다. 제품 차례는 최근 7일 라이브 매출이 큰 순이다 — 라이브에서 실제로
 * 팔리는 것이 위로 온다. 매출액 자체는 싣지 않는다.
 */
export default function DealSheet({
  items,
  summary,
  asOf,
  updated,
}: {
  items: DealItem[];
  summary: DealSummary;
  asOf: string;
  updated: string;
}) {
  const t = useT();
  const [고른띠, set고른띠] = useState<string | null>(null);
  const [찾기, set찾기] = useState("");

  const 보일것 = useMemo(() => {
    const q = 찾기.trim().toLowerCase();
    return items.filter((it) => {
      if (고른띠 && it.태그 !== 고른띠) return false;
      if (!q) return true;
      return (
        it.ko.toLowerCase().includes(q) ||
        it.en.toLowerCase().includes(q) ||
        it.pid.includes(q) ||
        it.sku.some((s) => s.이름.toLowerCase().includes(q))
      );
    });
  }, [items, 고른띠, 찾기]);

  const 띠별 = useMemo(() => {
    const m = new Map<string, number>();
    items.forEach((it) => m.set(it.태그, (m.get(it.태그) ?? 0) + 1));
    return 차례.filter((k) => m.has(k)).map((k) => [k, m.get(k)!] as const);
  }, [items]);

  return (
    <main className="pw-main bf">
      <Poster
        kicker={t("달바 US 틱톡샵 · BFCM", "d'Alba US TikTok Shop · BFCM")}
        title={t("딜 가격표", "Live deal price sheet")}
        sub={t(
          "방송에 거는 제품의 정가와 딜가, 할인율입니다.",
          "List price, deal price and discount for everything you can pin on air.",
        )}
        stats={[
          { 라벨ko: "제품", 라벨en: "Products", 값: String(summary.제품수) },
          { 라벨ko: "SKU", 라벨en: "SKUs", 값: String(summary.sku수) },
          { 라벨ko: "평균 할인", 라벨en: "Avg. discount", 값: `${summary.평균할인}%` },
          { 라벨ko: "최대 할인", 라벨en: "Max discount", 값: `${summary.최대할인}%` },
        ]}
        updated={updated}
        source={t(`${asOf} 자료 · 틱톡샵 셀러센터`, `${asOf} data · TikTok Shop Seller Center`)}
      />

      {/* 무엇을 기준으로 줄을 세웠는지가 이 화면에서 가장 먼저 물어보는 것이다. */}
      <p className="ps-order">
        {t(
          "매출 순서입니다 — 최근 7일 라이브 매출이 큰 제품부터. 매일 갱신합니다.",
          "Sorted by sales — highest live sales over the last 7 days first. Updated daily.",
        )}
      </p>

      <p className="ps-warn">
        {t(
          "증정품(GWP)은 수시로 바뀝니다. 방송 켜기 전에 샵 상품 페이지에서 구성과 가격을 꼭 다시 확인하세요.",
          "Free gifts (GWP) change often. Always check the shop listing for the current gift and price right before you go live.",
        )}
      </p>

      <div className="ps-tools">
        <input
          type="search"
          value={찾기}
          onChange={(e) => set찾기(e.target.value)}
          placeholder={t("제품 이름이나 번호로 찾기", "Search by name or product ID")}
          aria-label={t("제품 찾기", "Search products")}
        />
        <div className="ps-chips" role="group" aria-label={t("묶음", "Groups")}>
          <button
            type="button"
            className={고른띠 === null ? "on" : ""}
            onClick={() => set고른띠(null)}
          >
            {t("전체", "All")} <em>{items.length}</em>
          </button>
          {띠별.map(([k, n]) => (
            <button
              key={k}
              type="button"
              className={`${고른띠 === k ? "on" : ""} bf-${k}`}
              onClick={() => set고른띠(고른띠 === k ? null : k)}
            >
              {t(띠[k].ko, 띠[k].en)} <em>{n}</em>
            </button>
          ))}
        </div>
      </div>

      {보일것.length === 0 ? (
        <p className="pw-none">{t("찾는 제품이 없습니다.", "No products match.")}</p>
      ) : (
        <ol className="bf-grid">
          {보일것.map((it, i) => (
            <li key={it.pid} className={`bf-card bf-${it.태그}`}>
              <div className="bf-card-top">
                <span className="bf-tag">{t(띠[it.태그].ko, 띠[it.태그].en)}</span>
                <span className="bf-sku-n">
                  {it.sku.length} {t("SKU", it.sku.length > 1 ? "SKUs" : "SKU")}
                </span>
              </div>

              <div className="bf-card-body">
                <div className="bf-shot">
                  {it.이미지 ? (
                    // 제품컷은 받아 둔 파일이다. 샵 주소는 서명값이 붙어 곧 막힌다.
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={it.이미지} alt="" loading="lazy" width={440} height={440} />
                  ) : (
                    <span className="bf-noshot" aria-hidden="true" />
                  )}
                  <span className="bf-rank" title={t("라이브 매출 순", "By live sales")}>
                    {i + 1}
                  </span>
                </div>

                <div className="bf-name">
                  <h2>{t(it.ko, it.en)}</h2>
                  <a href={shopUrl(it.pid)} target="_blank" rel="noreferrer">
                    PID {it.pid}
                    <span aria-hidden="true"> ↗</span>
                  </a>
                </div>
              </div>

              <table className="bf-sku">
                <tbody>
                  {it.sku.map((s) => (
                    <tr key={s.이름}>
                      <th scope="row">
                        {s.이름 === "Default"
                          ? t("기본", "Default")
                          : s.이름}
                      </th>
                      <td className="bf-was">{돈(s.정가)}</td>
                      <td className="bf-now">{돈(s.딜가)}</td>
                      <td>
                        <span className={`bf-off${s.할인 >= 50 ? " big" : ""}`}>
                          -{Math.round(s.할인)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </li>
          ))}
        </ol>
      )}

      <p className="bf-foot">
        {t(
          "가격은 셀러센터에 걸린 값을 하루에 한 번 옮겨 적습니다. 할인율이 크게 달라 보이면 샵 화면 쪽이 맞습니다.",
          "Prices are copied from Seller Center once a day. If a discount looks far off, the shop page is the one to trust.",
        )}
      </p>
    </main>
  );
}
