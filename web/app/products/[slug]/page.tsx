import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getImages,
  getProduct,
  products,
  type Doc,
  type Product,
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

/**
 * 모든 제품이 같은 목차를 갖는다.
 * 교안에 내용이 없어도 항목을 빼지 않고 "교안에 없습니다" 로 남긴다 —
 * 제품마다 페이지 구성이 달라지면 무엇이 빠졌는지 알 수가 없기 때문이다.
 */
const SECTIONS = [
  { id: "images", label: "이미지" },
  { id: "features", label: "제품 특징" },
  { id: "ingredients", label: "성분" },
  { id: "texture", label: "제형 · 기술 · 향" },
  { id: "tests", label: "시험 · 인증" },
  { id: "howto", label: "사용법" },
  { id: "who", label: "이런 분께" },
  { id: "gaps", label: "확인 필요" },
  { id: "raw", label: "교안 원문" },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

/** 목차를 흐리게 표시할지 정하려고, 섹션별로 내용이 있는지 미리 센다. */
function hasContent(p: Product, id: SectionId, imageCount: number): boolean {
  switch (id) {
    case "images":
      return imageCount > 0;
    case "features":
      return p.특징.length > 0;
    case "ingredients":
      return (p.섹션.성분?.length ?? 0) > 0;
    case "texture":
      return ["제형", "기술", "향"].some((k) => p.섹션[k]?.length);
    case "tests":
      return (
        p.시험.length > 0 ||
        p.문서.length > 0 ||
        p.수치문장.length > 0 ||
        (p.섹션.시험?.length ?? 0) > 0
      );
    case "howto":
      return (p.섹션.사용법?.length ?? 0) > 0 || p.용기메모.length > 0 || !!p.사용법이미지;
    case "who":
      return p.니즈.length > 0 || (p.섹션.추천?.length ?? 0) > 0;
    case "gaps":
      return true; // 없는 항목이 없으면 "없음" 이라고 적어 준다
    case "raw":
      return p.원문.length > 0;
  }
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
  const filled = new Set(
    SECTIONS.filter((s) => hasContent(p, s.id, imgs.length)).map((s) => s.id),
  );

  const spec: [string, string | undefined][] = [
    ["용량 · 가격", p.스펙.용량가격],
    ["출시", p.스펙.출시],
    ["리뉴얼", p.스펙.리뉴얼],
    ["기능성", p.스펙.기능성],
    ["타겟", p.스펙.타겟],
  ];
  const 제형기술향 = ["제형", "기술", "향"].flatMap((k) => p.섹션[k] ?? []);
  const 주의메모 = p.이미지메모.filter((m) => m.주의);

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
        {p.포지셔닝?.문구 && <p className="pw-hook">{p.포지셔닝.문구}</p>}
        {!!p.포지셔닝?.태그.length && (
          <p className="pw-tags">
            {p.포지셔닝.태그.map((t) => (
              <span key={t}>{t}</span>
            ))}
          </p>
        )}
      </header>

      <nav className="pw-toc" aria-label="목차">
        {SECTIONS.map((s) => (
          <a key={s.id} href={`#${s.id}`} className={filled.has(s.id) ? undefined : "off"}>
            {s.label}
          </a>
        ))}
      </nav>

      {/* 01 이미지 */}
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

      {/* 02 제품 특징 */}
      <section className="pw-sec" id="features">
        <h2>제품 특징</h2>
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

      {/* 03 성분 */}
      <section className="pw-sec" id="ingredients">
        <h2>성분</h2>
        {p.섹션.성분?.length ? <Blocks items={p.섹션.성분} /> : <Empty what="성분 설명" />}
      </section>

      {/* 04 제형 · 기술 · 향 */}
      <section className="pw-sec" id="texture">
        <h2>제형 · 기술 · 향</h2>
        {제형기술향.length ? <Blocks items={제형기술향} /> : <Empty what="제형·기술·향" />}
      </section>

      {/* 05 시험 · 인증 */}
      <section className="pw-sec" id="tests">
        <h2>시험 · 인증</h2>
        {filled.has("tests") ? (
          <>
            {!!p.시험.length && (
              <>
                <p className="pw-note">
                  아래 값은 교안의 그래프 <b>이미지 안에서 직접 읽은 것</b>입니다. 교안
                  텍스트에는 없습니다.
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
              </>
            )}

            {!!p.섹션.시험?.length && (
              <div className="pw-sub">
                <h3 className="pw-subhead">교안의 시험 슬라이드</h3>
                <Blocks items={p.섹션.시험} />
              </div>
            )}

            {!!p.수치문장.length && (
              <div className="pw-sub">
                <h3 className="pw-subhead">그 밖에 수치가 들어간 문장</h3>
                <ul className="pw-claims">
                  {p.수치문장.map((c, i) => (
                    <li key={i}>
                      <span className="pw-slideno">{c.슬라이드}</span>
                      {c.문장}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {!!p.문서.length && (
              <div className="pw-sub">
                <h3 className="pw-subhead">인증서 · 시험성적서</h3>
                <p className="pw-note">
                  일부 문서에는 신청인의 성명과 생년월일이 찍혀 있어{" "}
                  <b>원본 이미지는 싣지 않았습니다.</b> 내용만 옮겨 적었습니다.
                </p>
                <div className="pw-docs">
                  {p.문서.map((d, i) => (
                    <DocCard doc={d} key={i} />
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <Empty what="시험·인증" />
        )}
      </section>

      {/* 06 사용법 */}
      <section className="pw-sec" id="howto">
        <h2>사용법</h2>
        {filled.has("howto") ? (
          <>
            {p.사용법이미지 && <p className="pw-block-line">{p.사용법이미지.text}</p>}
            {!!p.섹션.사용법?.length && <Blocks items={p.섹션.사용법} />}
            {!!p.용기메모.length && (
              <div className="pw-sub">
                <h3 className="pw-subhead">용기 · 보관</h3>
                <div className="pw-blocks">
                  {p.용기메모.map((n, i) => (
                    <div className="pw-block" key={i}>
                      <p className="pw-block-head">
                        <span>{n.kind}</span>
                      </p>
                      <p className="pw-block-line">{n.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <Empty what="사용법" />
        )}
      </section>

      {/* 07 이런 분께 */}
      <section className="pw-sec" id="who">
        <h2>이런 분께</h2>
        {filled.has("who") ? (
          <>
            {!!p.니즈.length && (
              <ul className="pw-plain">
                {p.니즈.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            )}
            {!!p.섹션.추천?.length && (
              <div className="pw-sub">
                <h3 className="pw-subhead">교안의 추천 대상</h3>
                <Blocks items={p.섹션.추천} />
              </div>
            )}
          </>
        ) : (
          <Empty what="대상 고객" />
        )}
      </section>

      {/* 08 확인 필요 */}
      <section className="pw-sec" id="gaps">
        <h2>확인 필요</h2>
        {p.없는항목.length || 주의메모.length ? (
          <>
            {!!p.없는항목.length && (
              <>
                <p className="pw-note">
                  교안에 없는 항목입니다. 추측으로 채우지 않았으니 필요하면 상품기획팀에
                  확인해야 합니다.
                </p>
                <ul className="pw-gaps">
                  {p.없는항목.map((g) => (
                    <li key={g}>{g}</li>
                  ))}
                </ul>
              </>
            )}
            {!!주의메모.length && (
              <div className="pw-sub">
                <h3 className="pw-subhead">교안 안에서 서로 어긋나는 것</h3>
                <div className="pw-docs">
                  {주의메모.map((d, i) => (
                    <DocCard doc={d} key={i} />
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <p className="pw-empty">확인이 필요한 항목이 없습니다.</p>
        )}
      </section>

      {/* 09 교안 원문 */}
      <section className="pw-sec" id="raw">
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
              <span className="pw-raw-title">{s.제목 || "(제목 없음)"}</span>
              {s.이미지수 > 0 && <span className="pw-imgcount">이미지 {s.이미지수}</span>}
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
                            ri === 0 ? <th key={ci}>{cell}</th> : <td key={ci}>{cell}</td>,
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
              {!s.내용.length && !s.표.length && (
                <p className="pw-block-line pw-muted">이 슬라이드에는 글자가 없습니다.</p>
              )}
            </div>
          </details>
        ))}
      </section>
    </main>
  );
}
