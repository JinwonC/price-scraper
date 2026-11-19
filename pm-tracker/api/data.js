import { getRedis, dataKey, LEGACY_KEY, getSessionId, readBody, storageMissing } from "./_lib.js";

/**
 * PM 트래커 데이터 저장 API (서버리스 함수, Vercel). 로그인한 사람 본인 것만 읽고 쓴다.
 *
 *   GET  /api/data  → 내 데이터. 없으면 { data: null }.
 *   PUT  /api/data  → 내 데이터를 통째로 저장한다. (마지막 저장이 이김)
 *
 * 이관: 계정 도입 전 데이터(pm-tracker:data)는 환경변수 LEGACY_OWNER 에 적힌 아이디가
 * 처음 불러올 때 그 사람 것으로 복사된다. 원본 키는 백업으로 그대로 남긴다.
 */

export default async function handler(req, res) {
  // 브라우저·CDN 이 응답을 캐시해서 옛 데이터를 보여주지 않게 한다.
  res.setHeader("Cache-Control", "no-store, max-age=0");
  const redis = getRedis();
  if (!redis) return storageMissing(res);

  const id = getSessionId(req);
  if (!id) return res.status(401).json({ error: "not_logged_in" });

  try {
    if (req.method === "GET") {
      let data = await redis.get(dataKey(id)); // 객체로 되돌아온다(자동 역직렬화)
      const owner = (process.env.LEGACY_OWNER || "").trim().toLowerCase();
      if (!data && owner && id === owner) {
        const legacy = await redis.get(LEGACY_KEY);
        if (legacy) {
          await redis.set(dataKey(id), legacy, { nx: true });
          data = await redis.get(dataKey(id));
        }
      }
      return res.status(200).json({ data: data ?? null });
    }

    if (req.method === "PUT" || req.method === "POST") {
      const body = readBody(req);
      if (!body || !Array.isArray(body.tasks)) {
        return res.status(400).json({ error: "bad_payload" });
      }
      await redis.set(dataKey(id), body);
      return res.status(200).json({ ok: true });
    }

    res.setHeader("Allow", "GET, PUT");
    return res.status(405).json({ error: "method_not_allowed" });
  } catch (e) {
    console.error("data api error", e);
    return res.status(500).json({ error: "server_error", message: String(e) });
  }
}
