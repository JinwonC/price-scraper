import ProductPicker from "@/components/ProductPicker";
import { cards, products } from "@/lib/products";

// 교안 JSON 은 빌드 시점에 읽는다. 내용이 바뀌면 다시 배포하면 된다.
export const dynamic = "force-static";

export default function ProductsIndex() {
  return (
    <main className="pw-main">
      <h1 className="pw-h1">제품을 고르세요</h1>
      <p className="pw-intro">
        사내 제품 교안 {products.length}개를 정리한 것입니다. 제품을 누르면 브리프와
        이미지, 제품 특징, 그리고 성분·향·사용법 이야기를 볼 수 있습니다.
      </p>

      <ProductPicker cards={cards} />
    </main>
  );
}
