import ProductPicker from "@/components/ProductPicker";
import { cards, products } from "@/lib/products";

// 교안 JSON 은 빌드 시점에 읽는다. 내용이 바뀌면 다시 배포하면 된다.
export const dynamic = "force-static";

export default function ProductsIndex() {
  const 슬라이드합 = products.reduce((n, p) => n + p.슬라이드수, 0);

  return (
    <main className="pw-main">
      <h1 className="pw-h1">제품을 고르세요</h1>
      <p className="pw-intro">
        교안 {products.length}개, 슬라이드 {슬라이드합}장에서 뽑은 내용입니다. 제품을
        누르면 스펙·특징·성분·시험 수치·사용법을 한 화면에서 볼 수 있습니다.
      </p>

      <ProductPicker cards={cards} />
    </main>
  );
}
