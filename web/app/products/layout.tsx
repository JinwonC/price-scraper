import type { Metadata } from "next";
import Link from "next/link";
import "./products.css";

export const metadata: Metadata = {
  title: "달바 제품 교안",
  description: "사내 제품 교안을 제품별로 모아 봅니다.",
  robots: { index: false, follow: false }, // 사내용 — 검색엔진 노출 방지
};

export default function ProductsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="pw">
      <header className="pw-top">
        <Link className="pw-home" href="/products">
          달바 제품 교안
        </Link>
        <Link className="pw-alt" href="/reddit">
          레딧 모니터 →
        </Link>
      </header>
      {children}
      <footer className="pw-foot">
        <p>
          사내 제품 교안(PPTX)에서 자동으로 뽑아낸 내용입니다. 수치는 교안에 적힌
          그대로 옮겼고, 교안에 없는 항목은 채우지 않고 비워 두었습니다.
        </p>
        <p>
          교안 문구에는 <b>“본 문구는 화장품법에 의거하여 검토한 내용이 아닙니다”</b>{" "}
          각주가 붙어 있습니다. 사내 교육용이며, 어느 시장에서도 심의를 거친 광고
          문구가 아닙니다.
        </p>
      </footer>
    </div>
  );
}
