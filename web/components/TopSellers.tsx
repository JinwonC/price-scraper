"use client";

import Link from "next/link";
import { useState } from "react";
import { useT } from "@/components/Lang";
import type { TopItem } from "@/lib/products";

/**
 * US 틱톡샵에서 많이 팔린 10개를 맨 위에 보여준다.
 *
 * 크리에이터가 방송에서 제품을 걸려면 pid 가 필요하다. 그래서 순위·이름과
 * 함께 pid 를 눌러 복사할 수 있게 둔다. 매출액은 싣지 않는다.
 */
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

/** 목록 한 줄. 많이 팔린 10개와 라이브 목록이 같이 쓴다. */
function Row({
  it,
  번호,
  라이브표시,
}: {
  it: TopItem;
  번호: number;
  라이브표시?: boolean;
}) {
  const t = useT();
  const name = t(it.ko, it.en);
  return (
    <li className={it.판매중 ? undefined : "off"}>
      <span className="pw-rank" aria-hidden="true">
        {번호}
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
        <span className="pw-best-meta">
          <CopyPid pid={it.pid} />
          {/* 라이브에서도 잘 나가는 제품이라는 표시. 순서는 바꾸지 않는다. */}
          {라이브표시 && it.라이브순위 && (
            <span className="pw-live-tag">
              {t(`라이브 ${it.라이브순위}위`, `#${it.라이브순위} on live`)}
            </span>
          )}
        </span>
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

  return (
    <section className="pw-best" aria-labelledby="top-sellers">
      {/* 이 화면의 첫 제목이다. 그래서 h2 가 아니라 h1 이다. */}
      <h1 id="top-sellers">
        {t("많이 팔린 10개", "Top 10 by sales")}
        <span className="pw-best-as-of">
          {t(`US 스토어 · ${period.ko}`, `US store · ${period.en}`)}
        </span>
      </h1>
      <p className="pw-note">
        {t(
          "방송에서 제품을 걸 때 쓰는 번호입니다. 눌러서 복사하세요. 세트 구성은 단품 교안이 없어 번호만 있습니다.",
          "These are the product IDs you tag with. Click one to copy it. The bundles have no single-product page, so they show the ID only.",
        )}
      </p>

      <ol className="pw-best-list">
        {items.map((it) => (
          <Row key={it.pid} it={it} 번호={it.순위 ?? 0} 라이브표시 />
        ))}
      </ol>

      <h2 className="pw-best-sub">{t("라이브에서 잘 나가는 것", "Strong on live")}</h2>
      <p className="pw-note">
        {t(
          "라이브 매출만 따로 세면 10위 안에 드는데, 위 목록에는 없는 제품입니다. 방송을 켠다면 이쪽을 같이 보세요.",
          "These make the live-sales top 10 but not the list above. Worth a look if you're going live.",
        )}
      </p>
      <ol className="pw-best-list">
        {live.map((it) => (
          // 여기 번호는 라이브 순위다. 위 목록 번호와 헷갈리지 않게 표시도 같이 단다.
          <Row key={it.pid} it={it} 번호={it.라이브순위 ?? 0} 라이브표시 />
        ))}
      </ol>
    </section>
  );
}
