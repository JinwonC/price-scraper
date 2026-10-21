"use client";

import { useState } from "react";
import { useT } from "@/components/Lang";

/**
 * 제품 번호와 틱톡샵 판매 페이지 링크.
 *
 * 크리에이터가 방송에 제품을 걸려면 번호가, 물건을 확인하려면 판매 페이지가
 * 필요하다. 둘을 한 덩이로 둔다 — 왼쪽은 눌러 복사, 오른쪽은 새 창으로 열기.
 *
 * 주소는 /us/pdp/x/<pid> 꼴을 쓴다. 슬러그 자리는 실제로 쓰이지 않아 아무
 * 값이나 들어가도 되고, 짧은 주소(/view/product/<pid>)는 제품에 따라 퍼즐
 * CAPTCHA 를 띄운다. 이 주소는 그냥 열린다.
 */
export function shopUrl(pid: string) {
  return `https://shop.tiktok.com/us/pdp/x/${pid}`;
}

export default function ShopLink({ pid }: { pid: string }) {
  const t = useT();
  const [done, setDone] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(pid);
    } catch {
      // 클립보드를 막아 둔 브라우저. 번호는 화면에 그대로 있으니 직접 긁으면 된다.
      return;
    }
    setDone(true);
    setTimeout(() => setDone(false), 1400);
  }

  return (
    <span className="pw-shop">
      <button
        type="button"
        className="pw-shop-pid"
        onClick={copy}
        title={t("눌러서 번호 복사", "Click to copy the ID")}
        aria-label={t(`제품 번호 ${pid} 복사`, `Copy product ID ${pid}`)}
      >
        <span>{pid}</span>
        <em>{done ? t("복사됨", "Copied") : t("복사", "Copy")}</em>
      </button>
      <a
        className="pw-shop-go"
        href={shopUrl(pid)}
        target="_blank"
        rel="noreferrer"
      >
        {t("틱톡샵 링크", "TikTok Shop link")}
        <span aria-hidden="true">↗</span>
      </a>
    </span>
  );
}
