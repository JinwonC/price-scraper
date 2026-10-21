"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useT } from "@/components/Lang";

/**
 * 틱톡샵 상품 페이지에 걸려 있는 이미지들. 교안 맨 아래에 둔다.
 *
 * 크리에이터가 방송에 쓸 때 실제 판매 페이지와 같은 그림을 봐야 해서,
 * 교안 컷이 아니라 샵에 올라가 있는 것을 그대로 받아 둔 것이다.
 * 갤러리(정사각 제품컷)와 상세페이지 컷을 각각 옆으로 넘겨 본다.
 *
 * 캐러셀은 브라우저가 이미 잘하는 것(가로 스크롤 + 스크롤 스냅)에 기댄다.
 * 화살표는 한 칸씩 밀어 주는 거들기일 뿐이라, 자바스크립트가 멈춰도
 * 손가락으로 넘기는 것은 그대로 된다.
 */
export type Shot = { src: string; w: number; h: number };

function Carousel({ shots, label }: { shots: Shot[]; label: string }) {
  const t = useT();
  const 띠 = useRef<HTMLUListElement>(null);
  const [끝, set끝] = useState({ 왼쪽: true, 오른쪽: false });

  const 살피기 = useCallback(() => {
    const el = 띠.current;
    if (!el) return;
    const 남은 = el.scrollWidth - el.clientWidth - el.scrollLeft;
    set끝({ 왼쪽: el.scrollLeft < 8, 오른쪽: 남은 < 8 });
  }, []);

  useEffect(() => {
    살피기();
    const el = 띠.current;
    if (!el) return;
    el.addEventListener("scroll", 살피기, { passive: true });
    window.addEventListener("resize", 살피기);
    return () => {
      el.removeEventListener("scroll", 살피기);
      window.removeEventListener("resize", 살피기);
    };
  }, [살피기]);

  function 밀기(쪽: -1 | 1) {
    const el = 띠.current;
    if (!el) return;
    // 한 칸 + 사이 여백만큼. 칸 너비는 화면 폭에 따라 달라지므로 재서 쓴다.
    const 칸 = el.firstElementChild as HTMLElement | null;
    const 폭 = 칸 ? 칸.getBoundingClientRect().width + 10 : el.clientWidth * 0.8;
    el.scrollBy({ left: 쪽 * 폭, behavior: "smooth" });
  }

  return (
    <div className="pw-carousel">
      <div className="pw-carousel-head">
        <h3>{label}</h3>
        <span className="pw-carousel-count">{shots.length}</span>
        <div className="pw-carousel-arrows">
          <button
            type="button"
            onClick={() => 밀기(-1)}
            disabled={끝.왼쪽}
            aria-label={t("이전", "Previous")}
          >
            ‹
          </button>
          <button
            type="button"
            onClick={() => 밀기(1)}
            disabled={끝.오른쪽}
            aria-label={t("다음", "Next")}
          >
            ›
          </button>
        </div>
      </div>
      <ul className="pw-carousel-track" ref={띠}>
        {shots.map((s) => (
          <li key={s.src}>
            {/* 틱톡샵에서 받아 둔 그림이다. 설명 글이 따로 없어 alt 는 비워 둔다. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={s.src}
              alt=""
              width={s.w}
              height={s.h}
              loading="lazy"
              decoding="async"
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ShopGallery({
  갤러리,
  상세,
}: {
  갤러리: Shot[];
  상세: Shot[];
}) {
  const t = useT();
  if (!갤러리.length && !상세.length) return null;

  return (
    <section className="pw-shopimgs" id="shop-images">
      <h2>{t("틱톡샵 이미지", "TikTok Shop images")}</h2>
      <p className="pw-note">
        {t(
          "실제 판매 페이지에 걸려 있는 그림입니다. 방송 화면이나 설명에 쓰면 손님이 보는 상품과 어긋나지 않습니다.",
          "The images on the live listing. Use these on stream and what you show matches what shoppers see.",
        )}
      </p>
      {갤러리.length > 0 && (
        <Carousel shots={갤러리} label={t("제품컷", "Product shots")} />
      )}
      {상세.length > 0 && (
        <Carousel shots={상세} label={t("상세페이지", "Listing detail")} />
      )}
    </section>
  );
}
