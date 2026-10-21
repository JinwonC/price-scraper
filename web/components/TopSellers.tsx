"use client";

import Link from "next/link";
import { useState } from "react";
import { useT } from "@/components/Lang";
import type { TopItem } from "@/lib/products";

/**
 * US 틱톡샵에서 많이 팔린 10개를 맨 위에 보여준다.
 *
 * 전체 매출 순서와 크리에이터 라이브 순서를 눌러서 바꿔 본다. 둘은 여섯
 * 개가 겹치고 넷이 다르다. 라이브 전용 세트처럼 라이브에서만 도는 제품은
 * 전체 순서로는 아예 안 보이기 때문에 따로 볼 수 있어야 한다.
 *
 * 라이브 순위는 브랜드 자체 라이브(셀러)와 크리에이터 라이브를 더한 값이다.
 * 사내 '제품별 유입매출 RAW' 시트에서 뽑는다 — CRUVA 의 제품별 live_gmv 에는
 * 브랜드 라이브가 아예 안 들어 있어서다. 시트가 아직 안 채워져 합산을 못 하면
 * CRUVA 의 크리에이터 라이브 순위로 돌아가고, 그때는 라벨도 그렇게 바뀐다
 * (liveInfo.합산).
 *
 * 두 탭은 집계 기간이 다르다. 전체는 CRUVA 가 어제까지, 라이브는 수동 시트가
 * 채워진 날짜까지다. 그래서 기간을 탭마다 따로 적는다.
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
  liveInfo,
}: {
  items: TopItem[];
  live: TopItem[];
  period: { ko: string; en: string };
  liveInfo: { 합산: boolean; 기간: { ko: string; en: string } };
}) {
  const t = useT();
  const [기준, set기준] = useState<기준>("전체");
  const 전체인가 = 기준 === "전체";
  const 보는것 = 전체인가 ? items : live;
  const 이번기간 = 전체인가 ? period : liveInfo.기간;
  const 라이브이름 = liveInfo.합산
    ? t("라이브", "Live")
    : t("크리에이터 라이브", "Creator live");

  return (
    <section className="pw-best" aria-labelledby="top-sellers">
      {/* 이 화면의 첫 제목이다. 그래서 h2 가 아니라 h1 이다. */}
      <h1 id="top-sellers">
        {t("많이 팔린 10개", "Top 10 by sales")}
        <span className="pw-best-as-of">
          {t(`US 스토어 · ${이번기간.ko}`, `US store · ${이번기간.en}`)}
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
            {k === "전체" ? t("전체", "Total") : 라이브이름}
          </button>
        ))}
      </div>

      <p className="pw-note">
        {전체인가
          ? t(
              "모든 경로를 합친 매출 순서입니다. 번호를 눌러 복사하세요. 세트 구성은 단품 교안이 없어 번호만 있습니다.",
              "Ranked by sales across every channel. Click an ID to copy it. The bundles have no single-product page, so they show the ID only.",
            )
          : liveInfo.합산
            ? t(
                "라이브에서 팔린 것만 세운 순서입니다. 브랜드 공식 계정 라이브와 크리에이터 라이브를 함께 셉니다. 금액이 작아 순위가 자주 바뀝니다.",
                "Ranked by sales on live only — the brand's own lives and creator lives together. The numbers are small, so the order moves around.",
              )
            : t(
                "크리에이터 라이브에서 팔린 것만 세운 순서입니다. 브랜드 라이브 집계가 아직 들어오지 않아 이번에는 빠져 있습니다.",
                "Ranked by sales on creator lives only. The brand's own live figures haven't come in yet, so they're not counted this time.",
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
