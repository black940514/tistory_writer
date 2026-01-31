#!/bin/bash
# 논문 리뷰 생성 스크립트
# 사용법: ./review.sh "논문제목 또는 arXiv URL"

if [ -z "$1" ]; then
    echo "사용법: ./review.sh \"논문제목 또는 arXiv URL\""
    exit 1
fi

docker run --rm \
  -v "$(pwd)/output:/app/output" \
  -v "$(pwd)/config.yaml:/app/config.yaml" \
  -v "$(pwd)/prompts.yaml:/app/prompts.yaml" \
  tistory-writer python scripts/generate_single_output.py "$1"
