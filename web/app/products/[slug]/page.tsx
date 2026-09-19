import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getImages,
  getProduct,
  products,
  type Doc,
  type Section,
} from "@/lib/products";

export const dynamic = "force-static";

export function generateStaticParams() {
  return products.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = getProduct(slug);
  return { title: p ? `${p.ko} — 달바 제품 교안` : "달바 제품 교안" };
}

/** 인증서·보고서에서 옮겨 적은 항목. 원본 이미지는 싣지 않는다. */
function DocCard({ doc }: { doc: Doc }) {
  const { kind, 주의, ...rest } = doc;
  return (
    <div className="pw-doc">
      {kind && <p className="pw-doc-kind">{String(kind)}</p>}
      <dl>
        {Object.entries(rest)
          .filter(([k, v]) => v !== undefined && v !== "" && k !== "image")
          .map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{String(v)}</dd>
            </div>
          ))}
      </dl>
      {주의 && <p className="pw-warn">{String(주의)}</p>}
    </div>
  );
}

function SectionBlocks({ items }: { items: Section[] }) {
  return (
    <div className="pw-blocks">
      {items.map((s) => (
        <div className="pw-block" key={s.슬라이드}>
          <p className="pw-block-head">
            {s.제목}
            <span className="pw-slideno">슬라이드 {s.슬라이드}</span>
          </p>
          {s.내용.map((line, i) => (
            <p className="pw-block-line" key={i}>
              {line}
            </p>
          ))}
          {s.표.map((table, ti) => (
            <div className="pw-tablewrap" key={ti}>
              <table>
                <tbody>
                  {table.map((row, ri) => (
                    <tr key={ri}>
                      {row.map((cell, ci) =>
                        ri === 0 ? (
                          <th key={ci}>{cell}</th>
                        ) : (
                          <td key={ci}>{cell}</td>
                        ),
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = getProduct(slug);
  if (!p) notFound();

  const imgs = getImages(slug);
  const spec: [string, string | undefined][] = [
    ["용량 · 가격", p.스펙.용량가격],
    ["출시", p.스펙.출시],
    ["리뉴얼", p.스펙.리뉴얼],
    ["기능성", p.스펙.기능성],
    ["타겟", p.스펙.타겟],
  ];
  const 기타섹션 = ["제형", "기술", "향", "용기"] as const;

  return (
    <main className="pw-main">
      <Link className="pw-back" href="/products">
        ← 제품 목록
      </Link>

      <header className="pw-head">
        <h1 className="pw-h1">{p.ko || p.en}</h1>
        <p className="pw-en-big">{p.en}</p>
        <dl className="pw-spec">
          {spec
            .filter(([, v]) => v)
            .map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
        </dl>
        {p.포지셔닝?.문구 && <p className="pw-hook">{p.포지셔닝.문구}</p>}
        {!!p.포지셔닝?.태그.length && (
          <p className="pw-tags">
            {p.포지셔닝.태그.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </p>
        )}
      </header>

      {!!imgs.length && (
        <section className="pw-sec">
          <h2>이미지</h2>
          <div className="pw-gallery">
            {imgs.map((im) => (
              <figure key={im.src}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={im.src} alt={im.설명} width={im.w} height={im.h} loading="lazy" />
                <figcaption>{im.설명}</figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      {!!p.특징.length && (
        <section className="pw-sec">
          <h2>제품 특징</h2>
          <ol className="pw-feat">
            {p.특징.map((f, i) => (
              <li key={i}>
                <h3>{f.제목}</h3>
                {f.설명.map((line, j) => (
                  <p key={j}>{line}</p>
                ))}
              </li>
            ))}
          </ol>
        </section>
      )}

      {!!p.니즈.length && (
        <section className="pw-sec">
          <h2>이런 분들을 위해</h2>
          <ul className="pw-plain">
            {p.니즈.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </section>
      )}

      {!!p.시험.length && (
        <section className="pw-sec">
          <h2>시험 결과</h2>
          <p className="pw-note">
            아래 값은 교안의 그래프 <b>이미지 안에서 직접 읽은 것</b>입니다. 교안 텍스트에는
            없습니다.
          </p>
          <div className="pw-tests">
            {p.시험.map((t) => (
              <div className="pw-test" key={t.no + t.name}>
                <div className="pw-test-top">
                  <span className="pw-test-no">{t.no}</span>
                  <span className="pw-test-name">{t.name}</span>
                  <span className="pw-test-fig">{t.표시값 ?? t.figure}</span>
                </div>
                {t.before !== undefined && t.after !== undefined && (
                  <p className="pw-readout">
                    <span>사용 전</span>
                    <b>{t.표시전 ?? t.before.toLocaleString()}</b>
                    <span className="pw-arrow">→</span>
                    <span>{t.condition ?? "사용 후"}</span>
                    <b>{t.표시후 ?? t.after.toLocaleString()}</b>
                  </p>
                )}
                <dl className="pw-mini">
                  {t.condition && (
                    <div>
                      <dt>조건</dt>
                      <dd>{t.condition}</dd>
                    </div>
                  )}
                  {t.footnote && (
                    <div>
                      <dt>각주</dt>
                      <dd>{t.footnote}</dd>
                    </div>
                  )}
                </dl>
                {t.주의 && <p className="pw-warn">{t.주의}</p>}
              </div>
            ))}
          </div>
        </section>
      )}

      {!!p.수치문장.length && (
        <section className="pw-sec">
          <h2>교안에 적힌 수치 · 시험 문장</h2>
          <p className="pw-note">
            교안 본문에서 수치나 시험 표현이 들어간 줄만 모았습니다. 원문 그대로입니다.
          </p>
          <ul className="pw-claims">
            {p.수치문장.map((c, i) => (
              <li key={i}>
                <span className="pw-slideno">{c.슬라이드}</span>
                {c.문장}
              </li>
            ))}
          </ul>
        </section>
      )}

      {!!p.문서.length && (
        <section className="pw-sec">
          <h2>인증 · 시험 문서</h2>
          <p className="pw-note">
            교안에 실린 인증서·성적서에서 옮겨 적었습니다. 일부 문서에는 신청인의 성명과
            생년월일이 찍혀 있어 <b>원본 이미지는 싣지 않았습니다</b>.
          </p>
          <div className="pw-docs">
            {p.문서.map((d, i) => (
              <DocCard doc={d} key={i} />
            ))}
          </div>
        </section>
      )}

      {!!p.섹션.성분?.length && (
        <section className="pw-sec">
          <h2>성분</h2>
          <SectionBlocks items={p.섹션.성분} />
        </section>
      )}

      {!!p.섹션.시험?.length && (
        <section className="pw-sec">
          <h2>시험 슬라이드 원문</h2>
          <SectionBlocks items={p.섹션.시험} />
        </section>
      )}

      {기타섹션
        .filter((k) => p.섹션[k]?.length)
        .map((k) => (
          <section className="pw-sec" key={k}>
            <h2>{k}</h2>
            <SectionBlocks items={p.섹션[k]} />
          </section>
        ))}

      {(!!p.섹션.사용법?.length || p.사용법이미지) && (
        <section className="pw-sec">
          <h2>사용법</h2>
          {p.사용법이미지 && <p className="pw-block-line">{p.사용법이미지.text}</p>}
          {!!p.섹션.사용법?.length && <SectionBlocks items={p.섹션.사용법} />}
        </section>
      )}

      {!!p.용기메모.length && (
        <section className="pw-sec">
          <h2>용기 · 보관</h2>
          {p.용기메모.map((n, i) => (
            <div className="pw-block" key={i}>
              <p className="pw-block-head">{n.kind}</p>
              <p className="pw-block-line">{n.text}</p>
            </div>
          ))}
        </section>
      )}

      {!!p.섹션.추천?.length && (
        <section className="pw-sec">
          <h2>추천 대상</h2>
          <SectionBlocks items={p.섹션.추천} />
        </section>
      )}

      {!!p.이미지메모.length && (
        <section className="pw-sec">
          <h2>이미지에서 확인한 것</h2>
          <div className="pw-docs">
            {p.이미지메모.map((d, i) => (
              <DocCard doc={d} key={i} />
            ))}
          </div>
        </section>
      )}

      {!!p.없는항목.length && (
        <section className="pw-sec">
          <h2>교안에 없는 항목</h2>
          <p className="pw-note">
            추측으로 채우지 않았습니다. 필요하면 상품기획팀에 확인해야 합니다.
          </p>
          <ul className="pw-gaps">
            {p.없는항목.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="pw-sec">
        <h2>교안 원문</h2>
        <p className="pw-note">
          슬라이드 {p.슬라이드수}장 전체입니다. 위에서 분류되지 않은 내용도 여기에는 남아
          있습니다.
          {!!p.판독대상슬라이드.length && (
            <>
              {" "}
              글자가 거의 없는 슬라이드({p.판독대상슬라이드.join(", ")}번)는 내용이 이미지
              안에 있습니다.
            </>
          )}
        </p>
        {p.원문.map((s) => (
          <details className="pw-raw" key={s.no}>
            <summary>
              <span className="pw-slideno">{s.no}</span>
              {s.제목 || "(제목 없음)"}
              {s.이미지수 > 0 && <span className="pw-imgcount">이미지 {s.이미지수}</span>}
            </summary>
            {s.내용.map((line, i) => (
              <p className="pw-block-line" key={i}>
                {line}
              </p>
            ))}
            {s.표.map((table, ti) => (
              <div className="pw-tablewrap" key={ti}>
                <table>
                  <tbody>
                    {table.map((row, ri) => (
                      <tr key={ri}>
                        {row.map((cell, ci) =>
                          ri === 0 ? <th key={ci}>{cell}</th> : <td key={ci}>{cell}</td>,
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
            {!s.내용.length && !s.표.length && (
              <p className="pw-block-line pw-muted">
                이 슬라이드에는 글자가 없습니다.
              </p>
            )}
          </details>
        ))}
      </section>
    </main>
  );
}
