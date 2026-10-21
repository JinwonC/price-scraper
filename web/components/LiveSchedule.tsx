"use client";

import { useEffect, useMemo, useState } from "react";
import { useLang, useT } from "@/components/Lang";
import type { Slot } from "@/lib/schedule";

/**
 * 브랜드 자체 라이브 일정.
 *
 * 어필리에이트 크리에이터가 브랜드 라이브와 시간이 겹치지 않게 방송을 잡으려고
 * 보는 화면이다. 그래서 '지금 방송 중'과 '오늘' 을 눈에 띄게 두고, 지난 시간은
 * 눌러 둔다.
 *
 * 시각은 UTC 로 받아 두고 고른 시간대로 그때그때 적는다. 서머타임이 끼면
 * 같은 목록 안에서도 EDT 와 EST 가 섞이는데, Intl 이 그 날짜의 규칙으로
 * 적어 주므로 줄마다 꼬리표를 붙여 둔다.
 */
const 시간대들 = [
  { 키: "ET", zone: "America/New_York", ko: "동부", en: "Eastern" },
  { 키: "CT", zone: "America/Chicago", ko: "중부", en: "Central" },
  { 키: "MT", zone: "America/Denver", ko: "산악", en: "Mountain" },
  { 키: "PT", zone: "America/Los_Angeles", ko: "태평양", en: "Pacific" },
  { 키: "AKT", zone: "America/Anchorage", ko: "알래스카", en: "Alaska" },
  { 키: "HT", zone: "Pacific/Honolulu", ko: "하와이", en: "Hawaii" },
] as const;

type 키 = (typeof 시간대들)[number]["키"];
const KEY = "dalba-pw-tz";

/** 브라우저 시간대로 탭을 미리 골라 준다. 미국 밖이면 동부로 둔다. */
function 짐작() {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const 맞는 = 시간대들.find((z) => z.zone === tz);
    if (맞는) return 맞는.키;
    // 같은 시간대를 가리키는 다른 이름이 많다(Phoenix, Detroit, Juneau…).
    // 지금 이 순간의 오프셋이 같은 곳으로 보낸다.
    const 지금 = new Date();
    const 분 = (z: string) =>
      new Date(지금.toLocaleString("en-US", { timeZone: z })).getTime();
    const 내것 = 분(tz);
    const 가까운 = 시간대들
      .map((z) => ({ z, 차: Math.abs(분(z.zone) - 내것) }))
      .sort((a, b) => a.차 - b.차)[0];
    if (가까운 && 가까운.차 < 30 * 60 * 1000) return 가까운.z.키;
  } catch {
    // 시간대를 못 읽는 브라우저. 동부로 둔다.
  }
  return "ET" as 키;
}

export default function LiveSchedule({
  slots,
  asOf,
}: {
  slots: Slot[];
  asOf: string;
}) {
  const t = useT();
  const { lang } = useLang();
  const locale = lang === "ko" ? "ko-KR" : "en-US";
  const [tz, setTz] = useState<키>("ET");
  // 서버에서 그린 HTML 과 어긋나지 않게, 현재 시각은 화면에 올라온 뒤에 읽는다.
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    let 처음 = 짐작();
    try {
      const 저장 = localStorage.getItem(KEY);
      if (시간대들.some((z) => z.키 === 저장)) 처음 = 저장 as 키;
    } catch {
      // 저장소를 막아 둔 브라우저. 짐작한 값으로 둔다.
    }
    setTz(처음);
    setNow(Date.now());
    const 째깍 = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(째깍);
  }, []);

  function 고르기(k: 키) {
    setTz(k);
    try {
      localStorage.setItem(KEY, k);
    } catch {
      // 못 저장해도 이번 방문 동안은 고른 시간대로 보인다.
    }
  }

  const zone = 시간대들.find((z) => z.키 === tz)!.zone;

  const 날짜키 = useMemo(
    () => new Intl.DateTimeFormat("en-CA", { timeZone: zone }),
    [zone],
  );
  const 날짜글 = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        timeZone: zone,
        month: "long",
        day: "numeric",
        weekday: "short",
      }),
    [locale, zone],
  );
  const 시각글 = useMemo(
    () =>
      new Intl.DateTimeFormat(locale, {
        timeZone: zone,
        hour: "numeric",
        minute: "2-digit",
      }),
    [locale, zone],
  );
  const 꼬리표 = useMemo(
    () =>
      new Intl.DateTimeFormat("en-US", {
        timeZone: zone,
        timeZoneName: "short",
      }),
    [zone],
  );

  function 꼬리(iso: string) {
    const p = 꼬리표
      .formatToParts(new Date(iso))
      .find((x) => x.type === "timeZoneName");
    return p ? p.value : tz;
  }

  // 같은 현지 날짜끼리 묶는다. 자료는 이미 시각 순으로 들어온다.
  const 묶음 = useMemo(() => {
    const m = new Map<string, Slot[]>();
    for (const s of slots) {
      const k = 날짜키.format(new Date(s.시작));
      const 줄 = m.get(k);
      if (줄) 줄.push(s);
      else m.set(k, [s]);
    }
    return [...m.entries()];
  }, [slots, 날짜키]);

  const 오늘키 = now === null ? null : 날짜키.format(new Date(now));

  return (
    <section className="pw-sched">
      <h1>
        {t("브랜드 라이브 일정", "Brand live schedule")}
        <span className="pw-best-as-of">
          {t(`${asOf} 기준 · 매일 갱신`, `As of ${asOf} · updated daily`)}
        </span>
      </h1>

      <p className="pw-note">
        {t(
          "d'Alba 공식 계정이 직접 하는 라이브입니다. 이 시간대를 피해서 방송을 잡으면 같은 상품으로 서로 부딪히지 않습니다. 일정은 수시로 바뀌니 방송 전날 한 번 더 확인하세요.",
          "These are d'Alba's own live streams. Schedule around them so you're not competing with the brand on the same products. The plan changes often, so check again the day before you go live.",
        )}
      </p>

      <div
        className="pw-tz"
        role="group"
        aria-label={t("시간대", "Time zone")}
      >
        {시간대들.map((z) => (
          <button
            key={z.키}
            type="button"
            aria-pressed={tz === z.키}
            onClick={() => 고르기(z.키)}
          >
            {t(z.ko, z.en)}
          </button>
        ))}
      </div>

      {묶음.length === 0 ? (
        <p className="pw-note">
          {t(
            "예정된 브랜드 라이브가 없습니다.",
            "No brand lives on the schedule.",
          )}
        </p>
      ) : (
        <ol className="pw-sched-list">
          {묶음.map(([키, 줄들]) => (
            <li key={키}>
              <h2>
                {날짜글.format(new Date(줄들[0].시작))}
                {오늘키 === 키 && (
                  <span className="pw-today">{t("오늘", "Today")}</span>
                )}
              </h2>
              <ul>
                {줄들.map((s) => {
                  const 시작 = new Date(s.시작).getTime();
                  const 끝 = s.끝 ? new Date(s.끝).getTime() : null;
                  const 방송중 =
                    now !== null && 시작 <= now && (끝 === null || now < 끝);
                  const 지남 = now !== null && 끝 !== null && 끝 <= now;
                  return (
                    <li
                      key={s.시작 + s.계정en}
                      className={지남 ? "off" : undefined}
                    >
                      <span className="pw-sched-time">
                        {시각글.format(new Date(s.시작))}
                        {s.끝 && ` – ${시각글.format(new Date(s.끝))}`}
                        <em>{꼬리(s.시작)}</em>
                      </span>
                      <span className="pw-sched-who">
                        {t(s.계정ko, s.계정en)}
                      </span>
                      {방송중 && (
                        <span className="pw-onair">
                          {t("방송 중", "On air")}
                        </span>
                      )}
                      {s.확인필요 && (
                        <span className="pw-check">
                          {t("날짜 확인 중", "Date unconfirmed")}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
        </ol>
      )}

      <p className="pw-note pw-sched-foot">
        {t(
          "시각은 고른 시간대의 현지 시각입니다. 서머타임은 각 날짜의 규칙대로 적힙니다. 애리조나는 서머타임이 없어 여름에는 태평양, 겨울에는 산악 시간과 같습니다.",
          "Times are local to the zone you picked, with daylight saving applied per date. Arizona doesn't observe it, so it matches Pacific in summer and Mountain in winter.",
        )}
      </p>
    </section>
  );
}
