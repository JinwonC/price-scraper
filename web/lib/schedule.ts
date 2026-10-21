import sched from "@/data/live-schedule.json";

/**
 * 브랜드 자체 라이브 일정. 시각은 UTC 로 들어 있고, 화면에서 보는 사람이 고른
 * 미국 시간대로 다시 적는다. 원본 시트는 live-schedule/schedule.py 가 읽는다.
 */
export type Slot = {
  계정ko: string;
  계정en: string;
  시작: string;
  끝: string | null;
  /** 시트의 날짜 칸과 시각 칸이 어긋난 줄. 화면에 표시해 둔다. */
  확인필요?: boolean;
};

type File = { 기준: string; 일정: Slot[] };
const file = sched as File;

export const 일정: Slot[] = file.일정;
export const 일정기준: string = file.기준;
