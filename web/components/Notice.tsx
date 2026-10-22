"use client";

import { useEffect, useState } from "react";
import { useT } from "@/components/Lang";

/**
 * 첫 화면 맨 위 공지.
 *
 * 사장님이 구글 시트('공지' 탭)에 한 줄 쓰면 그대로 올라온다. 배포를 다시 할
 * 필요가 없도록, 화면이 열릴 때 시트를 csv 로 받아 온다. 시트를 못 읽으면
 * (공유가 풀렸거나 구글이 느릴 때) 저장소에 구워 둔 공지를 대신 보여준다 —
 * 그쪽은 매일 갱신 때 시트에서 다시 채운다.
 *
 * 시트 칸: 표시(Y/N) · 제목 · 본문 · 링크 · 링크문구 · 시작일 · 종료일 · 비고
 * 비고는 사람끼리 보는 칸이라 화면에 올리지 않는다.
 */
export type NoticeItem = {
  제목: string;
  본문: string;
  링크?: string;
  링크문구?: string;
  시작일?: string;
  종료일?: string;
};

/** 따옴표 안의 쉼표·줄바꿈까지 지키는 작은 csv 파서. */
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i++;
        } else {
          quoted = false;
        }
      } else {
        cell += c;
      }
    } else if (c === '"') {
      quoted = true;
    } else if (c === ",") {
      row.push(cell);
      cell = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += c;
    }
  }
  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }
  return rows;
}

/** 오늘(보는 사람 현지 날짜)이 시작일~종료일 안인지. 빈 칸은 '언제나' 다. */
function 기간안(it: NoticeItem) {
  const 오늘 = new Date();
  const ymd = `${오늘.getFullYear()}-${String(오늘.getMonth() + 1).padStart(2, "0")}-${String(오늘.getDate()).padStart(2, "0")}`;
  const 시작 = (it.시작일 || "").trim();
  const 종료 = (it.종료일 || "").trim();
  if (시작 && ymd < 시작) return false;
  if (종료 && ymd > 종료) return false;
  return true;
}

function 시트읽기(rows: string[][]): NoticeItem[] {
  if (!rows.length) return [];
  const 머리 = rows[0].map((h) => h.trim());
  const 자리 = (이름: string) => 머리.indexOf(이름);
  const [표시, 제목, 본문, 링크, 링크문구, 시작일, 종료일] = [
    "표시", "제목", "본문", "링크", "링크문구", "시작일", "종료일",
  ].map(자리);
  if (제목 < 0) return [];
  const out: NoticeItem[] = [];
  for (const r of rows.slice(1)) {
    const 켬 = 표시 < 0 ? "Y" : (r[표시] || "").trim().toUpperCase();
    if (켬 !== "Y" && 켬 !== "YES" && 켬 !== "TRUE") continue;
    const it: NoticeItem = {
      제목: (r[제목] || "").trim(),
      본문: (본문 < 0 ? "" : r[본문] || "").trim(),
      링크: 링크 < 0 ? "" : (r[링크] || "").trim(),
      링크문구: 링크문구 < 0 ? "" : (r[링크문구] || "").trim(),
      시작일: 시작일 < 0 ? "" : (r[시작일] || "").trim(),
      종료일: 종료일 < 0 ? "" : (r[종료일] || "").trim(),
    };
    if (!it.제목 && !it.본문) continue;
    if (!기간안(it)) continue;
    out.push(it);
  }
  return out;
}

export default function Notice({
  csv,
  baked,
}: {
  csv?: string;
  baked: NoticeItem[];
}) {
  const t = useT();
  // 서버에서 그린 HTML 과 어긋나지 않게, 구워 둔 공지도 화면에 올라온 뒤에 거른다.
  const [items, setItems] = useState<NoticeItem[]>([]);

  useEffect(() => {
    let 살아있음 = true;
    setItems(baked.filter(기간안));
    if (!csv) return;
    fetch(csv, { cache: "no-store" })
      .then((r) => (r.ok ? r.text() : Promise.reject(new Error(String(r.status)))))
      .then((text) => {
        if (!살아있음) return;
        const 새것 = 시트읽기(parseCsv(text));
        // 시트를 읽었으면 그쪽이 최신이다. 빈 시트도 '공지 없음' 이라는 뜻이라 그대로 따른다.
        setItems(새것);
      })
      .catch(() => {
        // 시트를 못 읽었다. 구워 둔 공지를 그대로 둔다.
      });
    return () => {
      살아있음 = false;
    };
  }, [csv, baked]);

  if (!items.length) return null;

  return (
    <section className="pw-notice" aria-label={t("공지", "Notices")}>
      {items.map((it, i) => (
        <article key={`${it.제목}-${i}`}>
          {it.제목 && <h2>{it.제목}</h2>}
          {it.본문.split("\n").map((line, j) =>
            line.trim() ? <p key={j}>{line}</p> : null,
          )}
          {it.링크 && (
            <a href={it.링크} target="_blank" rel="noreferrer">
              {it.링크문구 || t("자세히 보기", "Read more")}
              <span aria-hidden="true">↗</span>
            </a>
          )}
        </article>
      ))}
    </section>
  );
}
