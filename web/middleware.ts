import { NextRequest, NextResponse } from "next/server";

/**
 * 비밀번호 게이트 (HTTP Basic 인증).
 *
 * Vercel 배포 URL 은 기본적으로 아무나 접근할 수 있다. 사내 모니터링 화면이므로
 * 환경변수 SITE_PASSWORD 를 설정하면 비밀번호를 입력해야 열리게 한다.
 * (아이디는 아무거나 입력해도 되고, 비밀번호만 맞으면 통과)
 *
 * SITE_PASSWORD 를 설정하지 않으면 게이트 없이 공개된다.
 */
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

/** 길이·내용이 달라도 항상 같은 시간을 쓰도록 비교한다(타이밍 공격 방지). */
function safeEqual(a: string, b: string): boolean {
  const encoder = new TextEncoder();
  const aBytes = encoder.encode(a);
  const bBytes = encoder.encode(b);
  // 길이 자체가 새어나가지 않도록 고정 길이 버퍼에 담아 비교한다.
  const size = Math.max(aBytes.length, bBytes.length, 32);
  let diff = aBytes.length ^ bBytes.length;
  for (let i = 0; i < size; i++) {
    diff |= (aBytes[i] ?? 0) ^ (bBytes[i] ?? 0);
  }
  return diff === 0;
}

function unauthorized(): NextResponse {
  return new NextResponse("인증이 필요합니다.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="dalba-reddit-monitor", charset="UTF-8"',
      "Content-Type": "text/plain; charset=utf-8",
    },
  });
}

export function middleware(request: NextRequest) {
  const password = process.env.SITE_PASSWORD;
  if (!password) return NextResponse.next(); // 미설정 시 공개

  const header = request.headers.get("authorization");
  if (!header) return unauthorized();

  const [scheme, encoded] = header.split(" ");
  if (scheme !== "Basic" || !encoded) return unauthorized();

  let decoded: string;
  try {
    decoded = atob(encoded);
  } catch {
    return unauthorized();
  }

  // "아이디:비밀번호" 에서 첫 콜론 뒤 전부가 비밀번호(비밀번호에 콜론이 있어도 안전)
  const separator = decoded.indexOf(":");
  const supplied = separator === -1 ? "" : decoded.slice(separator + 1);

  return safeEqual(supplied, password) ? NextResponse.next() : unauthorized();
}
