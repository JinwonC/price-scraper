import { notFound } from "next/navigation";
import ProductView from "@/components/ProductView";
import { getBrief, getImages, getProduct, products } from "@/lib/products";

export const dynamic = "force-static";

export function generateStaticParams() {
  return products.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = getProduct(slug);
  return { title: p ? `${p.en || p.ko} — d'Alba Product Guide` : "d'Alba Product Guide" };
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const p = getProduct(slug);
  if (!p) notFound();

  // 두 언어를 모두 정적 HTML 에 담아 보낸다. 전환은 화면에서만 일어난다.
  return <ProductView p={p} brief={getBrief(slug)} imgs={getImages(slug)} />;
}
