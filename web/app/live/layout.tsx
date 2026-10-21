import type { Metadata } from "next";
import { LangProvider } from "@/components/Lang";
import Chrome from "@/components/Chrome";
// 교안 화면과 같은 스타일을 쓴다. 한 사이트이고 머리글·꼬리말이 같다.
import "../products/products.css";

export const metadata: Metadata = {
  title: "d'Alba Brand Live Schedule",
  description: "d'Alba's own live streams, so creators can schedule around them.",
  robots: { index: false, follow: false }, // 사내용 — 검색엔진 노출 방지
};

export default function LiveLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <LangProvider>
      <Chrome>{children}</Chrome>
    </LangProvider>
  );
}
