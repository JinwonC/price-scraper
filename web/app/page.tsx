import Dashboard from "@/components/Dashboard";
import { data } from "@/lib/data";

// 데이터는 빌드 시점에 JSON 에서 읽는다. 수집기가 JSON 을 커밋/푸시하면
// Vercel 이 자동으로 다시 배포하면서 최신 내용이 반영된다.
export const dynamic = "force-static";

export default function Page() {
  return <Dashboard payload={data} />;
}
