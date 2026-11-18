import { Redis } from "@upstash/redis";
import crypto from "node:crypto";

/**
 * 공용 도우미 (파일명이 _ 로 시작하면 Vercel 이 API 경로로 만들지 않는다).
 *
 * Redis 키
 *   pm-tracker:user:<id>   계정 { id, name, salt, hash, createdAt }
 *   pm-tracker:data:<id>   그 사람의 트래커 데이터
 *   pm-tracker:data        (옛날) 계정 도입 전 단일 데이터 — LEGACY_OWNER 계정으로 복사되고, 백업으로 그대로 둔다
 */

export const LEGACY_KEY = "pm-tracker:data";
export const userKey = (id) => `pm-tracker:user:${id}`;
export const dataKey = (id) => `pm-tracker:data:${id}`;

const url = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const token = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
const realRedis = url && token ? new Redis({ url, token }) : null;

// 로컬 테스트에서 가짜 저장소를 끼울 수 있게 globalThis 를 먼저 본다.
export function getRedis() {
  return globalThis.__PMT_REDIS__ || realRedis;
}

// 세션 서명 키: 따로 정하지 않았으면 KV 토큰(이미 비밀값)에서 만든다 → 환경변수 추가 없이도 동작.
function secret() {
  const s = process.env.SESSION_SECRET || token || globalThis.__PMT_SECRET__;
  if (!s) throw new Error("no_session_secret");
  return s;
}

/* ---------- 비밀번호 ---------- */
export function hashPassword(password, salt = crypto.randomBytes(16).toString("hex")) {
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return { salt, hash };
}
export function checkPassword(password, user) {
  const { hash } = hashPassword(password, user.salt);
  const a = Buffer.from(hash, "hex");
  const b = Buffer.from(user.hash, "hex");
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

/* ---------- 세션 쿠키 ---------- */
const COOKIE = "pmt_session";
const MAX_AGE = 60 * 60 * 24 * 30; // 30일

function sign(payload) {
  return crypto.createHmac("sha256", secret()).update(payload).digest("base64url");
}

export function setSession(res, id) {
  const payload = Buffer.from(JSON.stringify({ id, exp: Date.now() + MAX_AGE * 1000 })).toString("base64url");
  const value = `${payload}.${sign(payload)}`;
  res.setHeader("Set-Cookie", `${COOKIE}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${MAX_AGE}`);
}

export function clearSession(res) {
  res.setHeader("Set-Cookie", `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`);
}

/** 쿠키가 유효하면 계정 id, 아니면 null */
export function getSessionId(req) {
  const raw = req.headers?.cookie || "";
  const m = raw.split(/;\s*/).find((c) => c.startsWith(COOKIE + "="));
  if (!m) return null;
  const [payload, sig] = m.slice(COOKIE.length + 1).split(".");
  if (!payload || !sig) return null;
  const expected = sign(payload);
  if (sig.length !== expected.length || !crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null;
  try {
    const { id, exp } = JSON.parse(Buffer.from(payload, "base64url").toString());
    return exp > Date.now() ? id : null;
  } catch {
    return null;
  }
}

export function readBody(req) {
  return typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
}

export function storageMissing(res) {
  return res.status(503).json({
    error: "storage_not_configured",
    message: "저장소가 아직 연결되지 않았습니다. Vercel 프로젝트에 Upstash(KV) 스토리지를 붙이고 다시 배포해주세요.",
  });
}
