import ProductPicker from "@/components/ProductPicker";
import { cards, top10, top10기간 } from "@/lib/products";

// 교안 JSON 은 빌드 시점에 읽는다. 내용이 바뀌면 다시 배포하면 된다.
export const dynamic = "force-static";

export default function ProductsIndex() {
  // 값은 여기서 읽어 넘긴다. 화면 쪽에서 직접 가져오면 제품 데이터 전체가
  // 클라이언트 번들에 실린다.
  return <ProductPicker cards={cards} top={top10} period={top10기간} />;
}
