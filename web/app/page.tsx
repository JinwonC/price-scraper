import { redirect } from "next/navigation";

/**
 * 첫 화면은 제품 교안이다.
 * 레딧 모니터는 /reddit 으로 옮겼다 — 예전 주소로 들어오는 사람이 헤매지 않도록
 * 양쪽 화면 상단에 서로 가는 링크를 뒀다.
 */
export default function Home() {
  redirect("/products");
}
