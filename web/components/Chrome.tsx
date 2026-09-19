"use client";

import Link from "next/link";
import { LangSwitch, useT } from "@/components/Lang";

/** 상단 머리글과 아래 꼬리말. 언어 전환 버튼이 여기 산다. */
export default function Chrome({ children }: { children: React.ReactNode }) {
  const t = useT();
  return (
    <div className="pw">
      <header className="pw-top">
        <Link className="pw-home" href="/products">
          {t("달바 제품 교안", "d'Alba Product Guide")}
        </Link>
        <div className="pw-top-right">
          <LangSwitch />
          <Link className="pw-alt" href="/reddit">
            {t("레딧 모니터 →", "Reddit monitor →")}
          </Link>
        </div>
      </header>
      {children}
      <footer className="pw-foot">
        <p>
          {t(
            "사내 제품 교안에서 뽑아 정리한 내용입니다. 수치는 교안에 적힌 그대로 옮겼고, 교안에 없는 항목은 채우지 않고 비워 두었습니다.",
            "Compiled from d'Alba's internal product decks. Figures are copied exactly as printed; where the deck says nothing, the field is left empty rather than filled in.",
          )}
        </p>
        <p>
          {t(
            "교안 문구에는 “본 문구는 화장품법에 의거하여 검토한 내용이 아닙니다” 각주가 붙어 있습니다. 사내 교육용이며, 어느 시장에서도 심의를 거친 광고 문구가 아닙니다.",
            "The decks carry a footnote stating the copy has not been reviewed under Korean cosmetics law. This is internal training material, not cleared advertising copy in any market.",
          )}
        </p>
      </footer>
    </div>
  );
}
