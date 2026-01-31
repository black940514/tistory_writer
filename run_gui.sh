#!/bin/bash
# 논문 리뷰 발행 GUI 실행 스크립트

cd "$(dirname "$0")"

# Python 경로 확인
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌ Python이 설치되어 있지 않습니다."
    exit 1
fi

# GUI 실행 (논문 발행 GUI)
$PYTHON scripts/publish_gui.py

