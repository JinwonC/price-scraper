import type { Metadata } from "next";
import { LangProvider } from "@/components/Lang";
import Chrome from "@/components/Chrome";
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
    <LangProvider>
      <Chrome>{children}</Chrome>
    </LangProvider>
  );
}
