import raw from "@/data/products.json";
import images from "@/data/product-images.json";

/** 교안 한 슬라이드의 원문. 분류에 안 잡힌 내용까지 확인하려고 통째로 들고 있다. */
export type Slide = {
  no: number;
  제목: string;
  내용: string[];
  표: string[][][];
  이미지수: number;
};

/** 성분·사용법 같은 성격별 묶음 한 덩어리 (슬라이드 하나에 대응). */
export type Section = {
  슬라이드: number;
  제목: string;
  내용: string[];
  표: string[][][];
};

/** 이미지 안에서 직접 읽어낸 시험 결과. 교안 텍스트에는 없던 값들이다. */
export type Test = {
  no: string;
  name: string;
  before?: number;
  after?: number;
  /** 끝자리 0 이 의미 있는 값(61.810 등)은 교안에 인쇄된 문자열을 그대로 쓴다. */
  표시전?: string;
  표시후?: string;
  figure: string;
  표시값?: string;
  unit?: string;
  condition?: string;
  footnote?: string;
  image?: string;
  주의?: string;
};

/** 인증서·시험성적서에서 옮겨 적은 사실. 원본 이미지는 싣지 않는다(개인정보). */
export type Doc = Record<string, string | number | undefined>;

export type Product = {
  slug: string;
  en: string;
  ko: string;
  driveId: string;
  스펙: {
    이름?: string;
    출시?: string;
    리뉴얼?: string;
    용량가격?: string;
    기능성?: string;
    타겟?: string;
  };
  니즈: string[];
  포지셔닝: { 문구: string; 태그: string[] } | null;
  특징: { 제목: string; 설명: string[] }[];
  섹션: Record<string, Section[]>;
  수치문장: { 슬라이드: number; 문장: string }[];
  시험: Test[];
  문서: Doc[];
  이미지메모: Doc[];
  사용법이미지: { text: string; image: string } | null;
  용기메모: { kind: string; text: string; image?: string }[];
  슬라이드수: number;
  판독대상슬라이드: number[];
  없는항목: string[];
  원문: Slide[];
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

/**
 * 목록 화면이 쓰는 가벼운 색인.
 * products.json 은 800KB 가까이 되므로 클라이언트로 통째로 넘기지 않는다.
 */
export type ProductCard = {
  slug: string;
  ko: string;
  en: string;
  용량가격: string;
  기능성: string;
  한줄: string;
  태그: string[];
  대표이미지: string | null;
  시험수: number;
  슬라이드수: number;
  없는항목수: number;
};

export const cards: ProductCard[] = all.map((p) => ({
  slug: p.slug,
  ko: p.ko || p.en,
  en: p.en,
  용량가격: p.스펙.용량가격 ?? "",
  기능성: p.스펙.기능성 ?? "",
  한줄: p.포지셔닝?.문구 ?? "",
  태그: p.포지셔닝?.태그 ?? [],
  대표이미지: getImages(p.slug)[0]?.src ?? null,
  시험수: p.시험.length + p.수치문장.length,
  슬라이드수: p.슬라이드수,
  없는항목수: p.없는항목.length,
}));
