import { notFound } from "next/navigation";
import SetView from "@/components/SetView";
import { getSet, getShopImages, 세트들 } from "@/lib/products";

export const dynamic = "force-static";

export function generateStaticParams() {
  return 세트들.map((s) => ({ pid: s.pid }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ pid: string }>;
}) {
  const { pid } = await params;
  const s = getSet(pid);
  return {
    title: s
      ? `${s.en || s.ko} — d'Alba TikTok Shop Live`
      : "d'Alba TikTok Shop Live",
  };
}

export default async function SetPage({
  params,
}: {
  params: Promise<{ pid: string }>;
}) {
  const { pid } = await params;
  const s = getSet(pid);
  if (!s) notFound();

  // 세트는 교안이 없다. 샵에 걸려 있는 그림이 전부라 그것만 넘긴다.
  return <SetView item={s} shop={getShopImages(pid)} />;
}
