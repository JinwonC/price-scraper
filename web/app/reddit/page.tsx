import Link from "next/link";
import Dashboard from "@/components/Dashboard";
import { data } from "@/lib/data";

// 데이터는 빌드 시점에 JSON 에서 읽는다. 수집기가 JSON 을 커밋/푸시하면
// Vercel 이 자동으로 다시 배포하면서 최신 내용이 반영된다.
export const dynamic = "force-static";

export const metadata = {
  title: "달바 레딧 모니터",
  description: "레딧에서 오간 d'alba / dalba 언급을 매일 모아 봅니다.",
  robots: { index: false, follow: false },
};

export default function RedditPage() {
  return (
    <>
      <nav className="site-nav">
        <Link href="/products">← 제품 교안</Link>
        <span>레딧 모니터</span>
      </nav>
      <Dashboard payload={data} />
    </>
  );
}
