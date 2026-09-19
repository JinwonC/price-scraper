import raw from "@/data/products.json";
import images from "@/data/product-images.json";
import briefs from "@/data/briefs.json";

/** 브리프에 안 들어간 나머지를 사람이 읽고 풀어 쓴 것. 교안 원문이 아니다. */
export type Etc = { 제목: string; 본문: string[] };

export type Product = {
  slug: string;
  en: string;
  ko: string;
  스펙: { 용량?: string; 기능성?: string; 타겟?: string };
  포지셔닝: { 문구: string; 태그: string[] } | null;
  특징: { 제목: string; 설명: string[] }[];
  기타: Etc[];
};

export type ProductImage = {
  src: string;
  설명: string;
  w: number;
  h: number;
};

const all = raw as unknown as Product[];
const imageMap = images as unknown as Record<string, ProductImage[]>;

export const products: Product[] = all;

export function getProduct(slug: string): Product | undefined {
  return all.find((p) => p.slug === slug);
}

export function getImages(slug: string): ProductImage[] {
  return imageMap[slug] ?? [];
}

/** 목록 화면이 쓰는 가벼운 색인. 카드에 필요한 것만 담는다. */
export type ProductCard = {
  slug: string;
  ko: string;
  en: string;
  용량: string;
  기능성: string;
  한줄: string;
  태그: string[];
  대표이미지: string | null;
};

export const cards: ProductCard[] = all.map((p) => ({
  slug: p.slug,
  ko: p.ko || p.en,
  en: p.en,
  용량: p.스펙.용량 ?? "",
  기능성: p.스펙.기능성 ?? "",
  한줄: p.포지셔닝?.문구 ?? "",
  태그: p.포지셔닝?.태그 ?? [],
  대표이미지: getImages(p.slug)[0]?.src ?? null,
}));

/** 사람이 직접 쓴 브리프. 교안 추출 데이터와 달리 문장으로 읽히도록 쓴 것이다. */
export type Brief = {
  한줄: string;
  누구에게?: string;
  핵심성분?: { 이름: string; 함량?: string; 역할: string }[];
  근거수치?: { 항목: string; 값: string; 조건?: string }[];
  /** 수치의 시험 조건 한 줄. 보고서 번호·기관 주소 같은 건 넣지 않는다. */
  시험조건?: string;
  /** 어떤 인증이 있는지 이름만. 인증서 번호나 성적서 내용은 교안 원문에 있다. */
  인증?: string[];
  사용법?: { 이름: string; 방법: string }[];
  말할때?: { 문장: string; 근거: string }[];
  주의?: string[];
};

export function getBrief(slug: string): Brief | undefined {
  const map = briefs as unknown as Record<string, Brief | unknown>;
  const b = map[slug];
  return b && typeof b === "object" && "한줄" in (b as object)
    ? (b as Brief)
    : undefined;
}
