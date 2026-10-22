"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LangSwitch, useT } from "@/components/Lang";

/** 상단 머리글과 아래 꼬리말. 화면 전환과 언어 전환 버튼이 여기 산다. */
export default function Chrome({ children }: { children: React.ReactNode }) {
  const t = useT();
  const 여기 = usePathname() ?? "";
  return (
    <div className="pw">
      <header className="pw-top">
        <Link className="pw-home" href="/products">
          {t("달바 틱톡샵 라이브", "d'Alba TikTok Shop Live")}
        </Link>
        <div className="pw-top-right">
          <nav className="pw-nav" aria-label={t("화면", "Sections")}>
            <Link
              href="/products"
              aria-current={여기.startsWith("/products") ? "page" : undefined}
            >
              {t("제품", "Products")}
            </Link>
            <Link
              href="/live"
              aria-current={여기.startsWith("/live") ? "page" : undefined}
            >
              {t("라이브 일정", "Live schedule")}
            </Link>
          </nav>
          <LangSwitch />
        </div>
      </header>
      {children}
      <footer className="pw-foot">
        <p>
          {t(
            "제품별 정보를 한곳에 모았습니다. 수치는 브랜드 자료에 적힌 그대로이고, 확인되지 않은 항목은 비워 두었습니다.",
            "Product information, gathered in one place. Figures are reproduced exactly as the brand states them, and anything unconfirmed is left blank.",
          )}
        </p>
        <p>
          {t(
            "여기 적힌 문구는 어느 시장에서도 심의를 거친 광고 문구가 아닙니다. 방송에 쓰기 전에 해당 시장의 표시·광고 기준을 확인하세요.",
            "Nothing here is cleared advertising copy in any market. Check your own market's labelling and advertising rules before you use it on air.",
          )}
        </p>
      </footer>
    </div>
  );
}
