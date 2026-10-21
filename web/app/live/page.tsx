import LiveSchedule from "@/components/LiveSchedule";
import { 일정, 일정기준 } from "@/lib/schedule";

// 일정 JSON 은 빌드 시점에 읽는다. 하루에 한 번 갱신해 다시 배포한다.
export const dynamic = "force-static";

export default function LivePage() {
  // 값은 여기서 읽어 넘긴다. 화면 쪽에서 직접 가져오면 JSON 이 번들에 두 번 실린다.
  return <LiveSchedule slots={일정} asOf={일정기준} />;
}
