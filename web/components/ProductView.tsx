"use client";

import Link from "next/link";
import { useLang, useT } from "@/components/Lang";
import type { Brief, Product, ProductImage } from "@/lib/products";

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

const L = {
  back: ["← 제품 목록", "← All products"],
  brief: ["브리프", "Brief"],
  when: ["이럴 때", "For"],
  ingredients: ["핵심 성분", "Key ingredients"],
  howto: ["쓰는 법", "How to use"],
  say: ["이렇게 말하면 됩니다", "What you can say"],
  careful: ["말할 때 주의", "Careful with this"],
  images: ["이미지", "Images"],
  features: ["제품 특징", "Product features"],
  etc: ["기타", "More"],
  toc: ["목차", "Contents"],
  capacity: ["용량", "Size"],
  fn: ["기능성", "Functional claim"],
  target: ["타겟", "For"],
  featNote: [
    "브랜드가 정리한 제품의 셀링 포인트입니다.",
    "The brand's own selling points for this product.",
  ],
  etcNote: [
    "브리프에 다 넣기엔 긴 이야기들입니다. 성분이 무엇인지, 향이 어떻게 퍼지는지, 언제 쓰는 물건인지 — 방송 중에 질문이 들어올 만한 것들을 풀어 놓았습니다.",
    "The longer answers. What the ingredients actually are, how the scent moves, when you'd reach for it — the things that come up mid-stream.",
  ],
  noImages: ["준비 중입니다.", "Coming soon."],
  noFeat: ["준비 중입니다.", "Coming soon."],
  noEtc: ["준비 중입니다.", "Coming soon."],
  noBrief: ["준비 중입니다. 아래 내용을 참고하세요.", "Coming soon — see below."],
} as const;

function BriefBlock({ brief }: { brief: Brief }) {
  const t = useT();
  const e = brief.en;

  const 성분 = t(
    brief.핵심성분?.map((g) => ({ name: g.이름, amount: g.함량, role: g.역할 })),
    e?.ingredients,
  );
  const 수치 = t(
    brief.근거수치?.map((f) => ({ label: f.항목, value: f.값, note: f.조건 })),
    e?.figures,
  );
  const 사용법 = t(
    brief.사용법?.map((u) => ({ name: u.이름, how: u.방법 })),
    e?.howto,
  );
  const 말할때 = t(
    brief.말할때?.map((s) => ({ line: s.문장, why: s.근거 })),
    e?.say,
  );

  return (
    <section className="pw-brief" id="brief">
      <p className="pw-brief-tag">{t(L.brief[0], L.brief[1])}</p>
      <p className="pw-brief-lead">{t(brief.한줄, e?.lead)}</p>
      {(brief.누구에게 || e?.who) && (
        <p className="pw-brief-who">
          <span>{t(L.when[0], L.when[1])}</span>
          {t(brief.누구에게, e?.who)}
        </p>
      )}

      {!!수치?.length && (
        <div className="pw-figs">
          {수치.map((f) => (
            <div className="pw-fig" key={f.label}>
              <span className="pw-fig-num">{f.value}</span>
              <span className="pw-fig-name">{f.label}</span>
              {f.note && <span className="pw-fig-cond">{f.note}</span>}
            </div>
          ))}
        </div>
      )}

      {/* 수치가 없어도 시험 조건은 알려야 한다. 수치 타일 안에만 두면 조용히 사라진다. */}
      {(brief.시험조건 || e?.testNote) && (
        <p className="pw-fig-src">{t(brief.시험조건, e?.testNote)}</p>
      )}

      {!!t(brief.인증, e?.certs)?.length && (
        <p className="pw-certs">
          {t(brief.인증, e?.certs)!.map((c) => (
            <span key={c}>{c}</span>
          ))}
        </p>
      )}

      {!!성분?.length && (
        <div className="pw-brief-part">
          <h3>{t(L.ingredients[0], L.ingredients[1])}</h3>
          <ul className="pw-ing">
            {성분.map((g) => (
              <li key={g.name}>
                <span className="pw-ing-name">{g.name}</span>
                {g.amount && g.amount !== "-" && (
                  <span className="pw-ing-amt">{g.amount}</span>
                )}
                <span className="pw-ing-role">{g.role}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!!사용법?.length && (
        <div className="pw-brief-part">
          <h3>{t(L.howto[0], L.howto[1])}</h3>
          <ul className="pw-use">
            {사용법.map((u) => (
              <li key={u.name}>
                <span className="pw-use-name">{u.name}</span>
                <span>{u.how}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!!말할때?.length && (
        <div className="pw-brief-part">
          <h3>{t(L.say[0], L.say[1])}</h3>
          {말할때.map((s, i) => (
            <div className="pw-say" key={i}>
              <p className="pw-say-quote">{s.line}</p>
              <p className="pw-say-why">{s.why}</p>
            </div>
          ))}
        </div>
      )}

      {!!t(brief.주의, e?.careful)?.length && (
        <div className="pw-brief-part">
          <h3>{t(L.careful[0], L.careful[1])}</h3>
          <ul className="pw-careful">
            {t(brief.주의, e?.careful)!.map((c, i) => (
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

export default function ProductView({
  p,
  brief,
  imgs,
}: {
  p: Product;
  brief?: Brief;
  imgs: ProductImage[];
}) {
  const t = useT();
  const { lang } = useLang();
  const en = p.en판 ?? {};
  // 영어 화면에서는 영어로 쓴 값만 보여준다. 한국어가 섞여 남는 줄이 없도록.
  const spv = (ko?: string, e?: string) => (lang === "en" ? e : ko);

  // 가격·출시일은 사내 정보라 싣지 않는다. publish.py 에서 이미 걸러 둔다.
  const spec = (
    [
      [t(L.capacity[0], L.capacity[1]), spv(p.스펙.용량, en.스펙?.용량)],
      [t(L.fn[0], L.fn[1]), spv(p.스펙.기능성, en.스펙?.기능성)],
      [t(L.target[0], L.target[1]), spv(p.스펙.타겟, en.스펙?.타겟)],
    ] as [string, string | undefined][]
  ).filter(([, v]) => v);

  const 특징 = t(
    p.특징.map((f) => ({ title: f.제목, body: f.설명 })),
    en.특징,
  );
  const 기타 = p.기타.map((e) => ({
    title: t(e.제목, e.title),
    body: t(e.본문, e.body),
  }));

  return (
    <main className="pw-main">
      <Link className="pw-back" href="/products">
        {t(L.back[0], L.back[1])}
      </Link>

      <header className="pw-head">
        <h1 className="pw-h1">{t(p.ko || p.en, p.en)}</h1>
        {/* 영어 화면에서는 한국어 제품명을 띄우지 않는다. 읽을 수 없는 줄이 남는다. */}
        {t(p.en, "") && <p className="pw-en-big">{t(p.en, "")}</p>}
        <dl className="pw-spec">
          {spec.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      </header>

      {brief ? (
        <BriefBlock brief={brief} />
      ) : (
        <p className="pw-empty" style={{ marginTop: 26 }}>
          {t(L.noBrief[0], L.noBrief[1])}
        </p>
      )}

      <nav className="pw-toc" aria-label={t(L.toc[0], L.toc[1])}>
        {brief && <a href="#brief">{t(L.brief[0], L.brief[1])}</a>}
        <a href="#images" className={imgs.length ? undefined : "off"}>
          {t(L.images[0], L.images[1])}
        </a>
        <a href="#features" className={특징.length ? undefined : "off"}>
          {t(L.features[0], L.features[1])}
        </a>
        <a href="#etc">{t(L.etc[0], L.etc[1])}</a>
      </nav>

      <section className="pw-sec" id="images">
        <h2>{t(L.images[0], L.images[1])}</h2>
        {imgs.length ? (
          <div className="pw-gallery">
            {imgs.map((im) => (
              <figure key={im.src}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={im.src}
                  alt={t(im.설명, im.설명En)}
                  width={im.w}
                  height={im.h}
                  loading="lazy"
                />
                <figcaption>{t(im.설명, im.설명En)}</figcaption>
              </figure>
            ))}
          </div>
        ) : (
          <p className="pw-empty">{t(L.noImages[0], L.noImages[1])}</p>
        )}
      </section>

      <section className="pw-sec" id="features">
        <h2>{t(L.features[0], L.features[1])}</h2>
        <p className="pw-note">{t(L.featNote[0], L.featNote[1])}</p>
        {특징.length ? (
          <ol className="pw-feat">
            {특징.map((f, i) => (
              <li key={i}>
                <h3>{f.title}</h3>
                {f.body.map((line, j) => (
                  <p key={j}>{line}</p>
                ))}
              </li>
            ))}
          </ol>
        ) : (
          <p className="pw-empty">{t(L.noFeat[0], L.noFeat[1])}</p>
        )}
      </section>

      <section className="pw-sec" id="etc">
        <h2>{t(L.etc[0], L.etc[1])}</h2>
        <p className="pw-note">{t(L.etcNote[0], L.etcNote[1])}</p>
        {기타.length ? (
          <div className="pw-etc">
            {기타.map((e) => (
              <article key={e.title}>
                <h3>{e.title}</h3>
                {e.body.map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </article>
            ))}
          </div>
        ) : (
          <p className="pw-empty">{t(L.noEtc[0], L.noEtc[1])}</p>
        )}
      </section>
    </main>
  );
}
