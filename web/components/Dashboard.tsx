"use client";

import { useMemo, useState } from "react";
import TrendChart, { type Day } from "./TrendChart";
import type { Mention, Payload } from "@/lib/data";

const PERIODS = [
  { id: "7", label: "7일", days: 7 },
  { id: "30", label: "30일", days: 30 },
  { id: "90", label: "90일", days: 90 },
  { id: "all", label: "전체", days: 0 },
] as const;

type PeriodId = (typeof PERIODS)[number]["id"];

/** 수집기가 쓰는 것과 같은 표기 흔들림을 화면에서도 강조 표시한다. */
const BRAND_PATTERN = /(?:d\s*['’ʼ`]?\s*alba|달바)/gi;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * 본문에서 브랜드명(과 검색어)을 <mark> 로 감싼다.
 * 문자열을 조각내 React 노드로 만들기 때문에 HTML 주입 위험이 없다.
 */
function highlight(text: string, query: string) {
  const parts = [BRAND_PATTERN.source];
  if (query.trim()) parts.push(escapeRegExp(query.trim()));
  const pattern = new RegExp(`(${parts.join("|")})`, "gi");

  const pieces = text.split(pattern);
  return pieces.map((piece, i) =>
    // split 의 캡처 그룹 덕분에 홀수 인덱스가 매칭 조각이다
    i % 2 === 1 ? <mark key={i}>{piece}</mark> : <span key={i}>{piece}</span>,
  );
}

/** "YYYY-MM-DD" 에서 n일 전 키를 구한다. 시간대 영향을 받지 않게 UTC 로 계산. */
function shiftDay(dayKey: string, delta: number): string {
  const date = new Date(`${dayKey}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + delta);
  return date.toISOString().slice(0, 10);
}

function shortLabel(dayKey: string): string {
  const [, month, day] = dayKey.split("-");
  return `${Number(month)}/${Number(day)}`;
}

export default function Dashboard({ payload }: { payload: Payload }) {
  const [period, setPeriod] = useState<PeriodId>("30");
  const [kind, setKind] = useState("all");
  const [relevance, setRelevance] = useState("all");
  const [subreddit, setSubreddit] = useState("all");
  const [query, setQuery] = useState("");
  const [visible, setVisible] = useState(40);

  const items = payload.items;

  // 기준일은 "마지막 수집 시각". 빌드 시점과 열람 시점이 달라도 화면이 흔들리지
  // 않고, 데이터가 멈추면 화면도 정직하게 그 시점을 가리킨다.
  const anchorDay = useMemo(() => {
    if (payload.updatedAt) return payload.updatedAt.slice(0, 10);
    if (items.length) return items[0].date.slice(0, 10);
    return new Date().toISOString().slice(0, 10);
  }, [payload.updatedAt, items]);

  const periodDays = PERIODS.find((p) => p.id === period)?.days ?? 30;
  const cutoffDay = periodDays ? shiftDay(anchorDay, -(periodDays - 1)) : "";

  const subreddits = useMemo(() => {
    const names = new Set(items.map((m) => m.subreddit).filter(Boolean));
    return [...names].sort((a, b) => a.localeCompare(b));
  }, [items]);

  const kinds = useMemo(() => {
    const names = new Set(items.map((m) => m.kind).filter(Boolean));
    return [...names].sort();
  }, [items]);

  // 필터는 아래의 모든 것(통계·차트·목록)을 동일하게 좁힌다.
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return items.filter((m) => {
      const day = m.date.slice(0, 10);
      if (cutoffDay && day < cutoffDay) return false;
      if (kind !== "all" && m.kind !== kind) return false;
      if (relevance !== "all" && m.relevance !== relevance) return false;
      if (subreddit !== "all" && m.subreddit !== subreddit) return false;
      if (needle) {
        const haystack = `${m.title} ${m.body} ${m.subreddit} ${m.author}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      return true;
    });
  }, [items, cutoffDay, kind, relevance, subreddit, query]);

  const stats = useMemo(() => {
    const related = filtered.filter((m) => m.relevance === "관련").length;
    const subs = new Set(filtered.map((m) => m.subreddit).filter(Boolean));
    return { total: filtered.length, related, unsure: filtered.length - related, subs: subs.size };
  }, [filtered]);

  const days: Day[] = useMemo(() => {
    const span = periodDays || 90; // "전체" 는 최근 90일을 그린다
    const counts = new Map<string, number>();
    for (const m of filtered) {
      const day = m.date.slice(0, 10);
      counts.set(day, (counts.get(day) ?? 0) + 1);
    }
    const result: Day[] = [];
    for (let i = span - 1; i >= 0; i--) {
      const key = shiftDay(anchorDay, -i);
      result.push({ key, short: shortLabel(key), count: counts.get(key) ?? 0 });
    }
    return result;
  }, [filtered, anchorDay, periodDays]);

  const isFiltered =
    kind !== "all" || relevance !== "all" || subreddit !== "all" || query.trim() !== "";

  function resetFilters() {
    setKind("all");
    setRelevance("all");
    setSubreddit("all");
    setQuery("");
    setVisible(40);
  }

  if (!items.length) {
    return (
      <main className="page">
        <Masthead updatedAt={payload.updatedAt} total={0} />
        <div className="card empty-state">
          <h2>아직 수집된 언급이 없습니다</h2>
          <p>
            GitHub 리포지토리의 <strong>Actions</strong> 탭에서{" "}
            <em>Reddit Dalba Monitor</em> 를 한 번 실행하면 이 화면이 채워집니다.
            수집에는 이미 등록돼 있는 <code>APIFY_TOKEN</code> 을 그대로 쓰므로
            따로 준비할 키는 없습니다.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      <Masthead updatedAt={payload.updatedAt} total={payload.total} />

      {/* 필터 한 줄 — 기간이 맨 앞, 아래 내용 전체를 좁힌다 */}
      <div className="filters">
        <label className="field">
          <span>기간</span>
          <div className="segmented" role="group" aria-label="기간 선택">
            {PERIODS.map((p) => (
              <button
                key={p.id}
                type="button"
                aria-pressed={period === p.id}
                onClick={() => {
                  setPeriod(p.id);
                  setVisible(40);
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </label>

        <label className="field">
          <span>종류</span>
          <select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setVisible(40);
            }}
          >
            <option value="all">전체</option>
            {kinds.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>관련도</span>
          <select
            value={relevance}
            onChange={(e) => {
              setRelevance(e.target.value);
              setVisible(40);
            }}
          >
            <option value="all">전체</option>
            <option value="관련">관련</option>
            <option value="확인필요">확인필요</option>
          </select>
        </label>

        <label className="field">
          <span>서브레딧</span>
          <select
            value={subreddit}
            onChange={(e) => {
              setSubreddit(e.target.value);
              setVisible(40);
            }}
          >
            <option value="all">전체</option>
            {subreddits.map((s) => (
              <option key={s} value={s}>
                r/{s}
              </option>
            ))}
          </select>
        </label>

        <label className="field" style={{ flex: "1 1 220px" }}>
          <span>검색</span>
          <input
            type="search"
            placeholder="제목·내용·작성자에서 찾기"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setVisible(40);
            }}
          />
        </label>

        {isFiltered && (
          <button type="button" className="reset" onClick={resetFilters}>
            필터 초기화
          </button>
        )}
      </div>

      <div className="kpis">
        <Kpi label="언급" value={stats.total} sub={periodLabel(period)} />
        <Kpi label="관련" value={stats.related} dot="good" sub="브랜드 얘기로 보이는 것" />
        <Kpi label="확인필요" value={stats.unsure} dot="warning" sub="동명이인 등 섞였을 수 있음" />
        <Kpi label="서브레딧" value={stats.subs} sub="언급이 나온 커뮤니티 수" />
      </div>

      <TrendChart days={days} />

      <div className="list-head">
        <h2>언급 목록</h2>
        <span className="count">
          {stats.total.toLocaleString("ko-KR")}건 중 {Math.min(visible, stats.total).toLocaleString("ko-KR")}건 표시
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="card empty-state">
          <h2>조건에 맞는 언급이 없습니다</h2>
          <p>기간을 넓히거나 필터를 초기화해 보세요.</p>
        </div>
      ) : (
        <>
          <ul className="list">
            {filtered.slice(0, visible).map((m) => (
              <MentionCard key={m.id} mention={m} query={query} />
            ))}
          </ul>
          {visible < filtered.length && (
            <button type="button" className="more" onClick={() => setVisible((v) => v + 40)}>
              더 보기 ({(filtered.length - visible).toLocaleString("ko-KR")}건 남음)
            </button>
          )}
        </>
      )}
    </main>
  );
}

function periodLabel(period: PeriodId): string {
  const found = PERIODS.find((p) => p.id === period);
  return found?.days ? `최근 ${found.label}` : "전체 기간";
}

function Masthead({ updatedAt, total }: { updatedAt: string | null; total: number }) {
  return (
    <header className="masthead">
      <div>
        <h1>달바 레딧 모니터</h1>
        <p>레딧에서 오간 d&apos;alba / dalba 이야기를 매일 모읍니다.</p>
      </div>
      <span className="updated">
        {updatedAt
          ? `마지막 수집 ${updatedAt.slice(0, 16).replace("T", " ")} · 누적 ${total.toLocaleString("ko-KR")}건`
          : "아직 수집 전"}
      </span>
    </header>
  );
}

function Kpi({
  label,
  value,
  sub,
  dot,
}: {
  label: string;
  value: number;
  sub: string;
  dot?: "good" | "warning";
}) {
  return (
    <div className="card kpi">
      <div className="label">
        {dot && <span className={`dot ${dot}`} aria-hidden="true" />}
        {label}
      </div>
      <div className="value">{value.toLocaleString("ko-KR")}</div>
      <div className="sub">{sub}</div>
    </div>
  );
}

function MentionCard({ mention, query }: { mention: Mention; query: string }) {
  const isRelated = mention.relevance === "관련";
  return (
    <li className="mention">
      <div className="meta">
        <span className="tag sub">r/{mention.subreddit}</span>
        <span className="tag">{mention.kind}</span>
        <span className="tag">
          <span className={`dot ${isRelated ? "good" : "warning"}`} aria-hidden="true" />
          {mention.relevance}
        </span>
        <span className="sep">·</span>
        <time dateTime={mention.date.replace(" ", "T")}>{mention.date}</time>
      </div>

      <h3>
        <a href={mention.url} target="_blank" rel="noreferrer noopener">
          {highlight(mention.title || "(제목 없음)", query)}
        </a>
      </h3>

      {mention.body && <p className="body">{highlight(mention.body, query)}</p>}

      <footer>
        <span>u/{mention.author}</span>
        <span>▲ {Number(mention.score || 0).toLocaleString("ko-KR")}</span>
        {mention.comments !== "" && (
          <span>댓글 {Number(mention.comments).toLocaleString("ko-KR")}</span>
        )}
        <a href={mention.url} target="_blank" rel="noreferrer noopener">
          레딧에서 보기 ↗
        </a>
      </footer>
    </li>
  );
}
