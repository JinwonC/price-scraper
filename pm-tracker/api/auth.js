import {
  getRedis, userKey, hashPassword, checkPassword,
  setSession, clearSession, getSessionId, readBody, storageMissing,
} from "./_lib.js";

/**
 * 계정 API
 *   GET  /api/auth                                → 로그인 상태 { user: {id,name} } 또는 401
 *   POST /api/auth {action:"signup", id, password, name}
 *   POST /api/auth {action:"login",  id, password}
 *   POST /api/auth {action:"logout"}
 *
 * 가입은 각자 한다. 초대코드는 없다 — 주소를 아는 사람은 누구나 가입할 수 있고,
 * 가입한 사람은 자기 데이터만 본다.
 */

const ID_RE = /^[a-z0-9._-]{3,20}$/;

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store, max-age=0");
  const redis = getRedis();
  if (!redis) return storageMissing(res);

  try {
    if (req.method === "GET") {
      const id = getSessionId(req);
      const user = id ? await redis.get(userKey(id)) : null;
      if (!user) return res.status(401).json({ error: "not_logged_in" });
      return res.status(200).json({ user: { id: user.id, name: user.name } });
    }

    if (req.method !== "POST") {
      res.setHeader("Allow", "GET, POST");
      return res.status(405).json({ error: "method_not_allowed" });
    }

    const body = readBody(req);
    const id = String(body.id || "").trim().toLowerCase();
    const password = String(body.password || "");

    if (body.action === "logout") {
      clearSession(res);
      return res.status(200).json({ ok: true });
    }

    if (body.action === "signup") {
      if (!ID_RE.test(id)) return res.status(400).json({ error: "bad_id", message: "아이디는 영문 소문자·숫자·._- 로 3~20자예요." });
      if (password.length < 6) return res.status(400).json({ error: "bad_password", message: "비밀번호는 6자 이상이에요." });
      const name = String(body.name || "").trim().slice(0, 20) || id;

      const { salt, hash } = hashPassword(password);
      const user = { id, name, salt, hash, createdAt: new Date().toISOString() };
      // nx: 이미 있는 아이디면 저장하지 않는다(동시에 같은 아이디로 가입해도 하나만 성공)
      const ok = await redis.set(userKey(id), user, { nx: true });
      if (!ok) return res.status(409).json({ error: "id_taken", message: "이미 있는 아이디예요." });

      setSession(res, id);
      return res.status(200).json({ user: { id, name } });
    }

    if (body.action === "login") {
      const user = id ? await redis.get(userKey(id)) : null;
      if (!user || !checkPassword(password, user)) {
        return res.status(401).json({ error: "bad_login", message: "아이디 또는 비밀번호가 맞지 않아요." });
      }
      setSession(res, id);
      return res.status(200).json({ user: { id: user.id, name: user.name } });
    }

    return res.status(400).json({ error: "bad_action" });
  } catch (e) {
    console.error("auth api error", e);
    return res.status(500).json({ error: "server_error", message: String(e) });
  }
}
