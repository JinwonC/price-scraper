import raw from "@/data/mentions.json";

/** 수집기(reddit-dalba-monitor)가 만드는 항목 한 건. */
export type Mention = {
  id: string;
  /** 작성 시각(UTC epoch 초). 정렬·기간 필터의 기준 */
  ts: number;
  /** 사람이 읽는 작성 시각 (KST, "YYYY-MM-DD HH:mm") */
  date: string;
  kind: "포스트" | "댓글(언급)" | "댓글(발견)" | "댓글(반응)" | string;
  subreddit: string;
  title: string;
  body: string;
  author: string;
  score: number;
  /** 포스트만 값이 있고 댓글은 빈 문자열 */
  comments: number | string;
  relevance: "관련" | "확인필요" | string;
  keywords: string[];
  url: string;
};

export type Payload = {
  /** 마지막 수집 시각 (KST ISO). 아직 한 번도 안 돌았으면 null */
  updatedAt: string | null;
  total: number;
  items: Mention[];
};

const payload = raw as Payload;

/** 혹시 데이터가 뒤섞여 들어와도 화면은 항상 최신순으로 보이게 한다. */
export const data: Payload = {
  ...payload,
  items: [...(payload.items ?? [])].sort((a, b) => b.ts - a.ts),
};
