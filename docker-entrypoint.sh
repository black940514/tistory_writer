#!/bin/bash
set -e

# data 디렉토리 권한 확인 및 수정 (root 권한으로 실행)
if [ -d "/app/data" ]; then
    # data 디렉토리에 쓰기 권한 부여
    chmod -R 777 /app/data 2>/dev/null || true
    # appuser에게 소유권 부여 (UID 10001)
    chown -R 10001:10001 /app/data 2>/dev/null || true
fi

# Selenium 캐시 디렉토리 생성 및 권한 설정
mkdir -p /app/.cache/selenium/chrome 2>/dev/null || true
chmod -R 777 /app/.cache 2>/dev/null || true
chown -R 10001:10001 /app/.cache 2>/dev/null || true

# HOME 환경 변수가 /nonexistent로 설정되어 있으면 /app으로 변경
if [ "$HOME" = "/nonexistent" ] || [ -z "$HOME" ]; then
    export HOME=/app
fi

# appuser로 전환하여 명령 실행
if [ "$(id -u)" = "0" ]; then
    # root로 실행 중이면 appuser로 전환
    exec gosu 10001 "$@"
else
    # 이미 non-root 사용자로 실행 중이면 그대로 실행
    exec "$@"
fi

