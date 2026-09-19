import Link from "next/link";
import { notFound } from "next/navigation";
import { getBrief, getImages, getProduct, products, type Brief } from "@/lib/products";

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

  // 가격·출시일은 사내 정보라 싣지 않는다. publish.py 에서 이미 걸러 둔다.
  const spec: [string, string | undefined][] = [
    ["용량", p.스펙.용량],
    ["기능성", p.스펙.기능성],
    ["타겟", p.스펙.타겟],
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
          이 제품은 아직 브리프를 쓰지 않았습니다. 아래 기타 항목을 참고하세요.
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
        <a href="#etc">기타</a>
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

      <section className="pw-sec" id="etc">
        <h2>기타</h2>
        <p className="pw-note">
          브리프에 다 넣기엔 긴 이야기들입니다. 성분이 무엇인지, 향이 어떻게
          퍼지는지, 언제 쓰는 물건인지 — 방송 중에 질문이 들어올 만한 것들을
          풀어 놓았습니다.
        </p>
        {p.기타.length ? (
          <div className="pw-etc">
            {p.기타.map((e) => (
              <article key={e.제목}>
                <h3>{e.제목}</h3>
                {e.본문.map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </article>
            ))}
          </div>
        ) : (
          <p className="pw-empty">이 제품은 아직 기타를 쓰지 않았습니다.</p>
        )}
      </section>
    </main>
  );
}
