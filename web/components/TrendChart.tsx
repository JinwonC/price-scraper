"use client";

import { useState } from "react";

/** globals.css 의 .bars 높이와 맞춰야 한다. */
const PLOT_HEIGHT = 148;
const TOOLTIP_HALF = 58;
const TOOLTIP_HEIGHT = 46;

export type Day = {
  /** "YYYY-MM-DD" (버킷이면 시작일) */
  key: string;
  /** 축에 쓰는 짧은 표기 "M/D" */
  short: string;
  count: number;
  /** 툴팁에 보여줄 날짜 표기. 주 단위로 묶이면 "시작 ~ 끝" */
  tip?: string;
};

/** y축 눈금이 깔끔한 수(1/2/5의 배수)로 떨어지게 올림한다. */
function niceMax(value: number): number {
  if (value <= 4) return 4;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 2.5, 5, 10]) {
    const candidate = step * magnitude;
    if (candidate >= value) return Math.ceil(candidate);
  }
  return Math.ceil(value);
}

/**
 * 일별 언급 수 칼럼 차트.
 *
 * 계열이 하나뿐이라 범례는 두지 않는다(제목이 곧 계열 이름).
 * 값은 막대마다 적지 않고 호버·포커스 툴팁과 아래 목록이 대신한다.
 */
export default function TrendChart({
  days,
  unit = "일별",
  rangeLabel,
}: {
  days: Day[];
  /** "일별" 또는 "주별" — 막대 하나가 무엇인지 제목에서 밝힌다 */
  unit?: string;
  /** 실제로 그려진 구간. 조용히 잘라내지 않고 명시한다 */
  rangeLabel?: string;
}) {
  const [active, setActive] = useState<number | null>(null);

  const max = niceMax(Math.max(1, ...days.map((d) => d.count)));
  const mid = max / 2;

  const axisLabels = days.length
    ? [days[0].short, days[Math.floor((days.length - 1) / 2)].short, days[days.length - 1].short]
    : [];

  return (
    <section className="card chart-card">
      <div className="chart-head">
        <h2>{unit} 언급 수</h2>
        <span className="hint">{rangeLabel}</span>
      </div>

      <div className="plot">
        <div className="y-axis" aria-hidden="true">
          <span>{max.toLocaleString("ko-KR")}</span>
          <span>{mid.toLocaleString("ko-KR")}</span>
          <span>0</span>
        </div>

        <div className="plot-area">
          <div className="gridlines" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>

          <div className="bars">
            {days.map((day, index) => {
              const height = (day.count / max) * 100;
              return (
                <button
                  key={day.key}
                  type="button"
                  className="slot"
                  // 히트 영역이 막대보다 훨씬 크다(칼럼 전체 높이)
                  onMouseEnter={() => setActive(index)}
                  onMouseLeave={() => setActive(null)}
                  onFocus={() => setActive(index)}
                  onBlur={() => setActive(null)}
                  aria-label={`${day.tip ?? day.key} ${day.count}건`}
                >
                  <span
                    className={day.count === 0 ? "bar zero" : "bar"}
                    style={day.count === 0 ? undefined : { height: `${height}%` }}
                  />
                </button>
              );
            })}
          </div>

          {active !== null && days[active] && (
            <div
              className="tooltip"
              role="status"
              style={{
                // 양 끝 막대에서도 툴팁이 카드 밖으로 삐져나가지 않게 가둔다
                // (TOOLTIP_HALF 는 툴팁 폭의 절반 어림값)
                left: `clamp(${TOOLTIP_HALF}px, ${
                  ((active + 0.5) / days.length) * 100
                }%, calc(100% - ${TOOLTIP_HALF}px))`,
                // 가장 높은 막대에서 툴팁이 차트 위로 넘치지 않도록 아래로 민다
                top: `${Math.max(
                  TOOLTIP_HEIGHT,
                  (1 - days[active].count / max) * PLOT_HEIGHT - 10,
                )}px`,
              }}
            >
              <div className="tip-value">
                <span className="tip-key" aria-hidden="true" />
                {days[active].count.toLocaleString("ko-KR")}건
              </div>
              <div className="tip-label">{days[active].tip ?? days[active].key}</div>
            </div>
          )}

          <div className="x-axis" aria-hidden="true">
            {axisLabels.map((label, i) => (
              <span key={`${label}-${i}`}>{label}</span>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
