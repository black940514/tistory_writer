"""
테스트용 포스트 작성 스크립트 (즉시 실행)
"""
import sys
import logging
from pathlib import Path

# scripts 모듈 import를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.main import TistoryAutoPoster

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    try:
        poster = TistoryAutoPoster()
        poster.create_post()
        print("✅ 포스트 작성 완료!")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

