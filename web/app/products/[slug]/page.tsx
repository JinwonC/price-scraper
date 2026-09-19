import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getBrief,
  getImages,
  getProduct,
  products,
  type Brief,
  type Doc,
  type Section,
} from "@/lib/products";

/** **굵게** 표시만 지원하는 최소 마크업. 주의 문구에서 핵심어를 강조하려고 쓴다. */
function Bold({ text }: { text: string }) {
  return (
    <>
      {text.split(/\*\*(.+?)\*\*/g).map((part, i) =>
        i % 2 === 1 ? <b key={i}>{part}</b> : <span key={i}>{part}</span>,
      )}
    </>
  );
}

function BriefBlock({ brief }: { brief: Brief }) {
  return (
    <section className="pw-brief" id="brief">
      <p className="pw-brief-tag">브리프</p>
      <p className="pw-brief-lead">{brief.한줄}</p>
      {brief.누구에게 && (
        <p className="pw-brief-who">
          <span>이럴 때</span>
          {brief.누구에게}
        </p>
      )}

      {!!brief.근거수치?.length && (
        <div className="pw-figs">
          {brief.근거수치.map((f) => (
            <div className="pw-fig" key={f.항목}>
              <span className="pw-fig-num">{f.값}</span>
              <span className="pw-fig-name">{f.항목}</span>
              {f.조건 && <span className="pw-fig-cond">{f.조건}</span>}
            </div>
          ))}
        </div>
      )}

      {/* 수치가 없어도 시험 조건은 알려야 한다. 수치 타일 안에만 두면 조용히 사라진다. */}
      {brief.시험조건 && <p className="pw-fig-src">{brief.시험조건}</p>}

      {!!brief.인증?.length && (
        <p className="pw-certs">
          {brief.인증.map((c) => (
            <span key={c}>{c}</span>
          ))}
        </p>
      )}

      {!!brief.핵심성분?.length && (
        <div className="pw-brief-part">
          <h3>핵심 성분</h3>
          <ul className="pw-ing">
            {brief.핵심성분.map((g) => (
              <li key={g.이름}>
                <span className="pw-ing-name">{g.이름}</span>
                {g.함량 && g.함량 !== "-" && <span className="pw-ing-amt">{g.함량}</span>}
                <span className="pw-ing-role">{g.역할}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!!brief.사용법?.length && (
        <div className="pw-brief-part">
          <h3>쓰는 법</h3>
          <ul className="pw-use">
            {brief.사용법.map((u) => (
              <li key={u.이름}>
                <span className="pw-use-name">{u.이름}</span>
                <span>{u.방법}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!!brief.말할때?.length && (
        <div className="pw-brief-part">
          <h3>이렇게 말하면 됩니다</h3>
          {brief.말할때.map((s, i) => (
            <div className="pw-say" key={i}>
              <p className="pw-say-quote">{s.문장}</p>
              <p className="pw-say-why">{s.근거}</p>
            </div>
          ))}
        </div>
      )}

      {!!brief.주의?.length && (
        <div className="pw-brief-part">
          <h3>말할 때 주의</h3>
          <ul className="pw-careful">
            {brief.주의.map((c, i) => (
              <li key={i}>
                <Bold text={c} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

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

function Empty({ what }: { what: string }) {
  return <p className="pw-empty">교안에 {what} 내용이 없습니다.</p>;
}

function Blocks({ items }: { items: Section[] }) {
  return (
    <div className="pw-blocks">
      {items.map((s) => (
        <div className="pw-block" key={`${s.슬라이드}-${s.제목}`}>
          {s.제목 ? (
            <p className="pw-block-head">
              <span>{s.제목}</span>
              <span className="pw-slideno">슬라이드 {s.슬라이드}</span>
            </p>
          ) : (
            // 교안 슬라이드 제목이 "성분 설명" 같은 라벨뿐이면 머리글을 만들지 않는다.
            <span className="pw-block-no">{s.슬라이드}</span>
          )}
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
        </div>
      ))}
    </div>
  );
}

/** 인증서·보고서에서 옮겨 적은 항목. 원본 이미지는 싣지 않는다(개인정보). */
function DocCard({ doc }: { doc: Doc }) {
  const { kind, 주의, ...rest } = doc;
  const rows = Object.entries(rest).filter(
    ([k, v]) => v !== undefined && v !== "" && k !== "image",
  );
  return (
    <div className="pw-doc">
      {kind && <p className="pw-doc-kind">{String(kind)}</p>}
      {rows.length > 0 && (
        <dl>
          {rows.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{String(v)}</dd>
            </div>
          ))}
        </dl>
      )}
      {주의 && <p className="pw-warn">{String(주의)}</p>}
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
  const brief = getBrief(slug);

  const spec: [string, string | undefined][] = [
    ["용량 · 가격", p.스펙.용량가격],
    ["출시", p.스펙.출시],
    ["리뉴얼", p.스펙.리뉴얼],
    ["기능성", p.스펙.기능성],
    ["타겟", p.스펙.타겟],
  ];

  // 교안 원문은 한 곳에 모아 접어 둔다. 전성분 나열처럼 크리에이터가 볼 일 없는
  // 내용이 많아서, 근거를 확인할 사람만 펼쳐 보게 한다.
  const 원문섹션: [string, Section[]][] = [
    ["성분", p.섹션.성분 ?? []],
    ["제형 · 기술 · 향", ["제형", "기술", "향"].flatMap((k) => p.섹션[k] ?? [])],
    ["시험", p.섹션.시험 ?? []],
    ["사용법", p.섹션.사용법 ?? []],
    ["추천 대상", p.섹션.추천 ?? []],
  ];

  return (
    <main className="pw-main">
      <Link className="pw-back" href="/products">
        ← 제품 목록
      </Link>

      <header className="pw-head">
        <h1 className="pw-h1">{p.ko || p.en}</h1>
        <p className="pw-en-big">{p.en}</p>
        <dl className="pw-spec">
          {spec.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd className={v ? undefined : "pw-dd-none"}>{v ?? "교안에 없음"}</dd>
            </div>
          ))}
        </dl>
      </header>

      {brief ? (
        <BriefBlock brief={brief} />
      ) : (
        <p className="pw-empty" style={{ marginTop: 26 }}>
          이 제품은 아직 브리프를 쓰지 않았습니다. 아래 교안 원문을 참고하세요.
        </p>
      )}

      <nav className="pw-toc" aria-label="목차">
        {brief && <a href="#brief">브리프</a>}
        <a href="#images" className={imgs.length ? undefined : "off"}>
          이미지
        </a>
        <a href="#features" className={p.특징.length ? undefined : "off"}>
          제품 특징
        </a>
        <a href="#source">교안 원문</a>
      </nav>

      <section className="pw-sec" id="images">
        <h2>이미지</h2>
        {imgs.length ? (
          <div className="pw-gallery">
            {imgs.map((im) => (
              <figure key={im.src}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={im.src} alt={im.설명} width={im.w} height={im.h} loading="lazy" />
                <figcaption>{im.설명}</figcaption>
              </figure>
            ))}
          </div>
        ) : (
          <Empty what="쓸 만한 이미지가" />
        )}
      </section>

      <section className="pw-sec" id="features">
        <h2>제품 특징</h2>
        <p className="pw-note">교안의 [제품 특징 및 베네핏] 을 그대로 옮긴 것입니다.</p>
        {p.특징.length ? (
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
        ) : (
          <Empty what="특징 정리" />
        )}
      </section>

      <section className="pw-sec" id="source">
        <h2>교안 원문</h2>
        <p className="pw-note">
          담당자가 근거를 확인할 때 쓰는 자료입니다. 전성분 나열처럼 방송에서 쓸 일 없는
          내용도 그대로 들어 있습니다. 슬라이드 {p.슬라이드수}장 전체.
          {!!p.판독대상슬라이드.length && (
            <>
              {" "}
              글자가 거의 없는 슬라이드({p.판독대상슬라이드.join(", ")}번)는 내용이 이미지
              안에 있습니다.
            </>
          )}
        </p>

        {원문섹션
          .filter(([, items]) => items.length)
          .map(([label, items]) => (
            <details className="pw-fold" key={label}>
              <summary>
                {label}
                <span className="pw-fold-n">{items.length}</span>
              </summary>
              <div className="pw-fold-body">
                <Blocks items={items} />
              </div>
            </details>
          ))}

        {!!p.수치문장.length && (
          <details className="pw-fold">
            <summary>
              수치가 들어간 문장
              <span className="pw-fold-n">{p.수치문장.length}</span>
            </summary>
            <div className="pw-fold-body">
              <ul className="pw-claims">
                {p.수치문장.map((c, i) => (
                  <li key={i}>
                    <span className="pw-slideno">{c.슬라이드}</span>
                    {c.문장}
                  </li>
                ))}
              </ul>
            </div>
          </details>
        )}

        {!!p.문서.length && (
          <details className="pw-fold">
            <summary>
              인증서 · 시험성적서
              <span className="pw-fold-n">{p.문서.length}</span>
            </summary>
            <div className="pw-fold-body">
              <p className="pw-note">
                일부 문서에는 신청인의 성명과 생년월일이 찍혀 있어{" "}
                <b>원본 이미지는 싣지 않았습니다.</b>
              </p>
              <div className="pw-docs">
                {p.문서.map((d, i) => (
                  <DocCard doc={d} key={i} />
                ))}
              </div>
            </div>
          </details>
        )}

        {!!p.없는항목.length && (
          <details className="pw-fold">
            <summary>
              교안에 없는 항목
              <span className="pw-fold-n">{p.없는항목.length}</span>
            </summary>
            <div className="pw-fold-body">
              <ul className="pw-gaps">
                {p.없는항목.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </div>
          </details>
        )}

        <details className="pw-fold">
          <summary>
            슬라이드별 원문
            <span className="pw-fold-n">{p.원문.length}</span>
          </summary>
          <div className="pw-fold-body">
            {p.원문.map((s) => (
              <details className="pw-raw" key={s.no}>
                <summary>
                  <span className="pw-slideno">{s.no}</span>
                  <span className="pw-raw-title">{s.제목 || "(제목 없음)"}</span>
                  {s.이미지수 > 0 && (
                    <span className="pw-imgcount">이미지 {s.이미지수}</span>
                  )}
                </summary>
                <div className="pw-raw-body">
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
                  {!s.내용.length && !s.표.length && (
                    <p className="pw-block-line pw-muted">
                      이 슬라이드에는 글자가 없습니다.
                    </p>
                  )}
                </div>
              </details>
            ))}
          </div>
        </details>
      </section>
    </main>
  );
}
