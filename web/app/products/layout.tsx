import type { Metadata } from "next";
import { LangProvider } from "@/components/Lang";
import Chrome from "@/components/Chrome";
import "./products.css";

export const metadata: Metadata = {
  title: "d'Alba TikTok Shop Live",
  description: "Product briefs, shop images and the brand live schedule, for creators.",
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
