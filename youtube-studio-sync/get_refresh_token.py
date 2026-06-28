"""
OAuth 리프레시 토큰 발급 헬퍼 (로컬 PC에서 딱 한 번만 실행)

목적:
  GitHub Actions 같은 무인 환경에서는 브라우저 로그인을 할 수 없으므로,
  본인 PC에서 한 번 로그인하여 '리프레시 토큰'을 발급받아 둡니다.
  이 토큰을 GitHub Secret(GOOGLE_OAUTH_REFRESH_TOKEN)에 넣으면
  이후로는 자동으로 액세스 토큰이 갱신됩니다.

사전 준비:
  1) Google Cloud Console에서 OAuth 클라이언트(데스크톱 앱) 생성
  2) 받은 client_secret JSON 파일을 이 폴더에 'client_secret.json' 으로 저장
     (또는 CLIENT_SECRET_FILE 환경변수로 경로 지정)

실행:
  pip install google-auth-oauthlib
  python get_refresh_token.py

실행하면 브라우저가 열리고, 채널을 소유한 구글 계정으로 로그인/동의하면
  터미널에 client_id / client_secret / refresh_token 이 출력됩니다.
"""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def main():
    client_secret_file = os.environ.get("CLIENT_SECRET_FILE", "client_secret.json")
    if not os.path.exists(client_secret_file):
        raise SystemExit(
            f"'{client_secret_file}' 파일을 찾을 수 없습니다.\n"
            "Google Cloud Console > 사용자 인증 정보에서 데스크톱 앱 OAuth 클라이언트를 만들고\n"
            "JSON을 내려받아 이 폴더에 client_secret.json 으로 저장하세요."
        )

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
    # 로컬 브라우저로 로그인. 포트 0 = 사용 가능한 포트 자동 선택.
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    print("\n========== 아래 값을 GitHub Secret 에 등록하세요 ==========")
    print(f"GOOGLE_OAUTH_CLIENT_ID     = {creds.client_id}")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET = {creds.client_secret}")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN = {creds.refresh_token}")
    print("=========================================================")
    if not creds.refresh_token:
        print(
            "\n⚠️ refresh_token 이 비어 있습니다. 이미 동의한 적이 있으면 발급되지 않습니다.\n"
            "   https://myaccount.google.com/permissions 에서 이 앱 접근권한을 제거한 뒤\n"
            "   다시 실행하세요."
        )


if __name__ == "__main__":
    main()
