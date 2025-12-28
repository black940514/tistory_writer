# syntax=docker/dockerfile:1

# ============================================================================
# Tistory 자동 포스팅 프로그램 Dockerfile
# ============================================================================
# 설계 원칙:
# 1. uv를 사용하여 빠른 의존성 설치 및 재현성 보장
# 2. 멀티 스테이지 빌드로 최종 이미지 크기 최소화
# 3. 비권한 사용자로 실행하여 보안 강화
# 4. 리눅스 환경에서 계속 실행되도록 설계
# ============================================================================

ARG PYTHON_VERSION=3.11.8
FROM python:${PYTHON_VERSION}-slim as base

# Python 최적화 환경 변수
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# uv 설치 (의존성 관리 전용)
RUN pip install --no-cache-dir uv

# 의존성 파일만 먼저 복사 (Docker 레이어 캐싱 최적화)
COPY requirements.txt ./

# uv pip install: requirements.txt 사용 (더 안정적)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-cache -r requirements.txt

# 소스 코드 복사
COPY . .

# Entrypoint 스크립트 복사 및 실행 권한 부여
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 필요한 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/.cache/uv /app/data && \
    chmod -R 755 /app

# 비권한 사용자 생성
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /app/.cache

# Entrypoint 설정 (entrypoint에서 root 권한으로 권한 조정 후 appuser로 전환)
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# uv 캐시 디렉토리 및 Python 경로 설정
ENV UV_CACHE_DIR=/app/.cache/uv \
    UV_NO_PROJECT=1 \
    PYTHONPATH=/app

# 기본 실행 명령
CMD ["python", "scripts/main.py"]

