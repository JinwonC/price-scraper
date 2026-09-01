import { Redis } from "@upstash/redis";

/**
 * PM 트래커 데이터 저장 API (서버리스 함수, Vercel).
 *
 *   GET  /api/data  → 저장된 데이터를 돌려준다. 없으면 { data: null }.
 *   PUT  /api/data  → 본문(JSON)을 통째로 저장한다. (마지막 저장이 이김)
 *
 * 저장소는 Upstash Redis(= Vercel 스토리지 "KV")에 키 하나로 보관한다.
 * DB 테이블 설계 없이 JSON 문서 한 덩어리만 넣고 뺀다 — 단일 사용자용이라 이걸로 충분.
 */

const KEY = "pm-tracker:data";

// Vercel 마켓플레이스 Upstash 연동은 KV_* 이름을, 직접 붙이면 UPSTASH_* 이름을 준다.
// 어느 쪽이 오든 되도록 둘 다 본다.
const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;

const redis = url && token ? new Redis({ url, token }) : null;

export default async function handler(req, res) {
  // 브라우저·CDN 이 응답을 캐시해서 옛 데이터를 보여주지 않게 한다.
  res.setHeader("Cache-Control", "no-store, max-age=0");

  if (!redis) {
    // 스토리지를 아직 안 붙였을 때: 화면이 죽지 않도록 친절히 알려준다.
    return res.status(503).json({
      error: "storage_not_configured",
      message:
        "저장소가 아직 연결되지 않았습니다. Vercel 프로젝트에 Upstash(KV) 스토리지를 붙이고 다시 배포해주세요.",
    });
  }

  try {
    if (req.method === "GET") {
      const data = await redis.get(KEY); // 객체로 되돌아온다(자동 역직렬화)
      return res.status(200).json({ data: data ?? null });
    }

    if (req.method === "PUT" || req.method === "POST") {
      const body = typeof req.body === "string" ? JSON.parse(req.body) : req.body;
      if (!body || !Array.isArray(body.tasks)) {
        return res.status(400).json({ error: "bad_payload" });
      }
      await redis.set(KEY, body);
      return res.status(200).json({ ok: true });
    }

    res.setHeader("Allow", "GET, PUT");
    return res.status(405).json({ error: "method_not_allowed" });
  } catch (e) {
    console.error("data api error", e);
    return res.status(500).json({ error: "server_error", message: String(e) });
  }
}
