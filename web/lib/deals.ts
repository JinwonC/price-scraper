import deals from "@/data/deal-prices.json";

/**
 * BFCM 딜 가격표. 정가·딜가·할인율은 샵에 걸린 값 그대로다.
 * 원본 시트는 deal-price/deal.py 가 읽어 web/data/deal-prices.json 으로 굽는다.
 */
export type DealSku = {
  이름: string;
  정가: number;
  딜가: number;
  할인: number;
};

export type DealItem = {
  pid: string;
  ko: string;
  en: string;
  /** 라이브 · 틱톡 · 신상 · 할인. 카드 머리 띠가 여기서 갈린다. */
  태그: string;
  이미지: string | null;
  sku: DealSku[];
};

export type DealSummary = {
  제품수: number;
  sku수: number;
  평균할인: number;
  최대할인: number;
};

type File = { 기준: string; 요약: DealSummary; 상품: DealItem[] };
const file = deals as File;

export const 딜상품: DealItem[] = file.상품;
export const 딜요약: DealSummary = file.요약;
export const 딜기준: string = file.기준;
