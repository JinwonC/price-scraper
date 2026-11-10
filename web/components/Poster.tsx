"use client";

import { useT } from "@/components/Lang";

/**
 * 화면 맨 위 노란 머리판.
 *
 * 가격표·제품 목록·라이브 일정이 같은 자료의 다른 면이라, 세 화면 모두 이
 * 머리판으로 연다. 보는 사람이 탭을 옮겨도 같은 자리에서 같은 것을 읽는다.
 *
 * `갱신` 은 UTC ISO 로 받아 미국 동부 시각으로 적는다. 샵도 크리에이터도
 * 동부 기준으로 움직이고, 날짜만 적어 두면 오늘 치가 언제 들어왔는지 모른다.
 */
export type Stat = { 라벨ko: string; 라벨en: string; 값: string };

export function 갱신글(iso: string, lang: "ko" | "en") {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const 적기 = new Intl.DateTimeFormat(lang === "ko" ? "ko-KR" : "en-US", {
    timeZone: "America/New_York",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  return `${적기.format(d)} ET`;
}

export default function Poster({
  kicker,
  title,
  sub,
  stats,
  updated,
  source,
  children,
}: {
  kicker: string;
  title: string;
  sub?: string;
  stats?: Stat[];
  /** UTC ISO. 있으면 '마지막 갱신' 줄이 붙는다. */
  updated?: string;
  /** 갱신 줄 뒤에 붙는 출처 한 마디. */
  source?: string;
  children?: React.ReactNode;
}) {
  const t = useT();
  const lang = t("ko", "en") as "ko" | "en";
  return (
    <header className="ps-head">
      <p className="ps-kicker">{kicker}</p>
      <h1 className="ps-h1">{title}</h1>
      {sub && <p className="ps-sub">{sub}</p>}
      {stats && stats.length > 0 && (
        <dl className="ps-stats">
          {stats.map((s) => (
            <div key={s.라벨en}>
              <dt>{t(s.라벨ko, s.라벨en)}</dt>
              <dd>{s.값}</dd>
            </div>
          ))}
        </dl>
      )}
      {(updated || source) && (
        <p className="ps-asof">
          {updated
            ? t(`마지막 갱신 ${갱신글(updated, "ko")}`, `Last update ${갱신글(updated, "en")}`)
            : ""}
          {updated && source ? " · " : ""}
          {source ?? ""}
        </p>
      )}
      {children}
    </header>
  );
}
