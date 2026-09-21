"use client";

import Link from "next/link";
import { useState } from "react";
import { useT } from "@/components/Lang";
import type { TopItem } from "@/lib/products";

/**
 * US 틱톡샵에서 많이 팔린 10개를 맨 위에 보여준다.
 *
 * 전체 매출 순서와 라이브 매출 순서를 눌러서 바꿔 본다. 둘은 여섯 개가
 * 겹치고 넷이 다르다. 라이브 전용 세트처럼 라이브에서만 도는 제품은
 * 전체 순서로는 아예 안 보이기 때문에 따로 볼 수 있어야 한다.
 *
 * 크리에이터가 방송에서 제품을 걸려면 pid 가 필요하다. 그래서 순위·이름과
 * 함께 pid 를 눌러 복사할 수 있게 둔다. 매출액은 싣지 않는다.
 */
type 기준 = "전체" | "라이브";

function CopyPid({ pid }: { pid: string }) {
  const t = useT();
  const [done, setDone] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(pid);
    } catch {
      // 클립보드를 막아 둔 브라우저. 번호는 화면에 그대로 있으니 직접 긁으면 된다.
      return;
    }
    setDone(true);
    setTimeout(() => setDone(false), 1400);
  }

  return (
    <button
      type="button"
      className="pw-pid"
      onClick={copy}
      title={t("눌러서 복사", "Click to copy")}
      aria-label={t(`제품 번호 ${pid} 복사`, `Copy product ID ${pid}`)}
    >
      <span>{pid}</span>
      <em>{done ? t("복사됨", "Copied") : t("복사", "Copy")}</em>
    </button>
  );
}

function Row({ it }: { it: TopItem }) {
  const t = useT();
  const name = t(it.ko, it.en);
  return (
    <li className={it.판매중 ? undefined : "off"}>
      <span className="pw-rank" aria-hidden="true">
        {it.순위}
      </span>
      {/* 제품컷은 틱톡샵 공식 이미지다. 못 받은 제품은 빈 자리로 둔다. */}
      <span className="pw-best-thumb">
        {it.이미지 && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={it.이미지} alt="" loading="lazy" width={44} height={44} />
        )}
      </span>
      <div className="pw-best-body">
        <p className="pw-best-name">
          {it.slug ? <Link href={`/products/${it.slug}`}>{name}</Link> : name}
          {!it.판매중 && (
            <span className="pw-off-tag">{t("판매 중단", "Not on sale")}</span>
          )}
        </p>
        <CopyPid pid={it.pid} />
      </div>
    </li>
  );
}

export default function TopSellers({
  items,
  live,
  period,
}: {
  items: TopItem[];
  live: TopItem[];
  period: { ko: string; en: string };
}) {
  const t = useT();
  const [기준, set기준] = useState<기준>("전체");
  const 보는것 = 기준 === "전체" ? items : live;

  return (
    <section className="pw-best" aria-labelledby="top-sellers">
      {/* 이 화면의 첫 제목이다. 그래서 h2 가 아니라 h1 이다. */}
      <h1 id="top-sellers">
        {t("많이 팔린 10개", "Top 10 by sales")}
        <span className="pw-best-as-of">
          {t(`US 스토어 · ${period.ko}`, `US store · ${period.en}`)}
        </span>
      </h1>

      <div className="pw-basis" role="group" aria-label={t("순위 기준", "Ranked by")}>
        {(["전체", "라이브"] as 기준[]).map((k) => (
          <button
            key={k}
            type="button"
            aria-pressed={기준 === k}
            onClick={() => set기준(k)}
          >
            {k === "전체" ? t("전체", "Total") : t("라이브", "Live")}
          </button>
        ))}
      </div>

      <p className="pw-note">
        {기준 === "전체"
          ? t(
              "모든 경로를 합친 매출 순서입니다. 번호를 눌러 복사하세요. 세트 구성은 단품 교안이 없어 번호만 있습니다.",
              "Ranked by sales across every channel. Click an ID to copy it. The bundles have no single-product page, so they show the ID only.",
            )
          : t(
              "라이브에서 팔린 것만 세운 순서입니다. 라이브는 전체 매출의 6% 남짓이라 금액이 작고 순위가 자주 바뀝니다.",
              "Ranked by live sales only. Live is about 6% of total sales, so the numbers are small and the order moves around.",
            )}
      </p>

      <ol className="pw-best-list">
        {보는것.map((it) => (
          <Row key={it.pid} it={it} />
        ))}
      </ol>
    </section>
  );
}
