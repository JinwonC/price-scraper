import ProductPicker from "@/components/ProductPicker";
import { cards } from "@/lib/products";

// 교안 JSON 은 빌드 시점에 읽는다. 내용이 바뀌면 다시 배포하면 된다.
export const dynamic = "force-static";

export default function ProductsIndex() {
  return <ProductPicker cards={cards} />;
}
