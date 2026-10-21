import raw from "@/data/products.json";
import images from "@/data/product-images.json";
import briefs from "@/data/briefs.json";
import top from "@/data/top10.json";
import liveRanks from "@/data/live-ranks.json";
import lines from "@/data/lines.json";
import tiktok from "@/../product-edu/tiktok-us.json";

/** 브리프에 안 들어간 나머지를 사람이 읽고 풀어 쓴 것. 교안 원문이 아니다. */
export type Etc = { 제목: string; 본문: string[]; title?: string; body?: string[] };

export type Feature = { 제목: string; 설명: string[] };
export type FeatureEn = { title: string; body: string[] };

/** 교안에서 나온 것들의 영어판. 번역이라기보다 영어로 다시 쓴 것이다. */
export type ProductEn = {
  스펙?: { 용량?: string; 기능성?: string; 타겟?: string };
  한줄?: string;
  특징?: FeatureEn[];
  이미지?: string[];
};

export type Product = {
  slug: string;
  en: string;
  ko: string;
  스펙: { 용량?: string; 기능성?: string; 타겟?: string };
  포지셔닝: { 문구: string; 태그: string[] } | null;
  특징: Feature[];
  기타: Etc[];
  en판: ProductEn;
};

export type ProductImage = {
  src: string;
  설명: string;
  설명En?: string;
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
  const list = imageMap[slug] ?? [];
  const en = all.find((p) => p.slug === slug)?.en판?.이미지 ?? [];
  // 영어 설명은 이미지 순서대로 적는다. 아직 안 쓴 것은 비워 두면 한국어가 나온다.
  return list.map((im, i) => ({ ...im, 설명En: en[i] ?? "" }));
}

/** US 틱톡샵에서 많이 팔린 제품. 금액은 싣지 않는다 — 순위와 pid 만. */
export type TopItem = {
  순위: number;
  pid: string;
  ko: string;
  en: string;
  /** 교안에 단품 페이지가 있으면 그 슬러그. 세트 구성이면 null. */
  slug: string | null;
  판매중: boolean;
  /** 틱톡샵 공식 제품컷을 받아 둔 자리. 못 받은 제품은 null. */
  이미지: string | null;
};

type TopFile = {
  전체: string[];
  라이브: string[];
  제품: Record<string, Omit<TopItem, "순위" | "pid">>;
  기간ko: string;
  기간en: string;
};
const topFile = top as TopFile;

/** pid 목록을 순위 붙은 줄로 편다. */
function 펴기(pids: string[]): TopItem[] {
  return pids.map((pid, i) => ({ 순위: i + 1, pid, ...topFile.제품[pid] }));
}

/** 전체 매출 기준 1~10위. */
export const top10: TopItem[] = 펴기(topFile.전체);

/** CRUVA 가 센 라이브 순위. 크리에이터(제휴) 라이브만 들어 있다. */
const top크리에이터라이브: TopItem[] = 펴기(topFile.라이브);

/** 어느 기간을 센 순위인지. 화면에 그대로 띄운다. */
export const top10기간 = {
  ko: (top as { 기간ko: string }).기간ko,
  en: (top as { 기간en: string }).기간en,
};

type LiveFile = {
  순위: string[];
  제품: Record<string, Omit<TopItem, "순위" | "pid">>;
  기간ko: string;
  기간en: string;
};
const liveFile = liveRanks as LiveFile;

/**
 * 라이브 순위.
 *
 * 쓸 수 있으면 브랜드 라이브 + 크리에이터 라이브를 합산한 시트 쪽 순위를 쓴다.
 * 시트가 아직 안 채워졌거나 집계가 비면 CRUVA 의 크리에이터 라이브 순위로
 * 돌아간다. 둘은 세는 범위가 달라서 라벨도 같이 바뀐다 — '합산' 이 false 면
 * 화면에 '크리에이터 라이브' 라고 적는다.
 */
const 합산있음 = liveFile.순위.length > 0;

export const top라이브: TopItem[] = 합산있음
  ? liveFile.순위.map((pid, i) => ({ 순위: i + 1, pid, ...liveFile.제품[pid] }))
  : top크리에이터라이브;

export const top라이브정보 = {
  합산: 합산있음,
  기간: 합산있음
    ? { ko: liveFile.기간ko, en: liveFile.기간en }
    : top10기간,
};

/** 10위 안에 드는 제품이면 그 순위. 목록 카드에 띠를 달 때 쓴다. */
export function getRank(slug: string): number | undefined {
  return top10.find((t) => t.slug === slug)?.순위;
}

/**
 * 교안 제품의 US 틱톡샵 제품 번호. 제품 화면의 '틱톡샵 링크' 가 이걸 쓴다.
 * 매칭은 product-edu/tiktok-us.json 에 적어 두었다(사람이 확인한 표다).
 */
const pid표: Record<string, string> = Object.fromEntries(
  Object.entries(tiktok as Record<string, unknown>)
    .filter(([k, v]) => !k.startsWith("_") && typeof v === "object" && v !== null)
    .map(([slug, v]) => [slug, String((v as { product_id?: string }).product_id ?? "")])
    .filter(([, pid]) => pid),
);

export function getShopPid(slug: string): string | null {
  return pid표[slug] ?? null;
}

export type ProductCard = {
  slug: string;
  ko: string;
  en: string;
  용량: string;
  기능성: string;
  한줄: string;
  태그: string[];
  대표이미지: string | null;
  /** 영어 화면에서 쓸 값. 아직 안 쓴 제품은 비어 있고, 그때는 한국어를 보여준다. */
  용량En: string;
  기능성En: string;
  한줄En: string;
  /** US 스토어 판매 순위. 10위 안에 들 때만 값이 있다. */
  순위?: number;
  /** 어느 라인에 묶이는지. lines.json 의 '키'. */
  라인: string;
};

/** 제품을 라인으로 묶은 것. 줄 안의 차례는 lines.json 에 적힌 순서다. */
export type Line = {
  키: string;
  ko: string;
  en: string;
  설명ko: string;
  설명en: string;
  제품: string[];
};
export const 라인들: Line[] = (lines as { 라인: Line[] }).라인;

/** 한 제품이 어느 라인 몇 번째인지. 목록을 라인 차례로 세울 때 쓴다. */
const 자리 = new Map<string, number>();
라인들.forEach((ln, i) =>
  ln.제품.forEach((slug, j) => 자리.set(slug, i * 1000 + j)),
);

export const cards: ProductCard[] = all.map((p) => ({
  slug: p.slug,
  ko: p.ko || p.en,
  en: p.en,
  용량: p.스펙.용량 ?? "",
  기능성: p.스펙.기능성 ?? "",
  한줄: p.포지셔닝?.문구 ?? "",
  태그: p.포지셔닝?.태그 ?? [],
  대표이미지: getImages(p.slug)[0]?.src ?? null,
  용량En: p.en판?.스펙?.용량 ?? "",
  기능성En: p.en판?.스펙?.기능성 ?? "",
  한줄En: p.en판?.한줄 ?? "",
  순위: getRank(p.slug),
  라인: 라인들.find((ln) => ln.제품.includes(p.slug))?.키 ?? "기타",
}));

// 목록은 라인 차례로 세운다. lines.json 을 고치면 화면 순서도 같이 바뀐다.
cards.sort(
  (a, b) => (자리.get(a.slug) ?? 1e9) - (자리.get(b.slug) ?? 1e9),
);

/** 사람이 직접 쓴 브리프. 교안 추출 데이터와 달리 문장으로 읽히도록 쓴 것이다. */
export type BriefEn = {
  lead: string;
  who?: string;
  ingredients?: { name: string; amount?: string; role: string }[];
  figures?: { label: string; value: string; note?: string }[];
  testNote?: string;
  certs?: string[];
  howto?: { name: string; how: string }[];
  say?: { line: string; why: string }[];
};

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
  en?: BriefEn;
};

export function getBrief(slug: string): Brief | undefined {
  const map = briefs as unknown as Record<string, Brief | unknown>;
  const b = map[slug];
  return b && typeof b === "object" && "한줄" in (b as object)
    ? (b as Brief)
    : undefined;
}

