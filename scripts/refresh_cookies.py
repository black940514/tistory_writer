"""
쿠키 갱신 스크립트 (브라우저 자동화)
"""
import sys
import yaml
import logging
from pathlib import Path

# 프로젝트 루트 경로
project_root = Path(__file__).parent.parent

# src 모듈 import를 위한 경로 추가
sys.path.insert(0, str(project_root))

from src.auth.browser_auth import BrowserAuth

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """쿠키 갱신 메인 함수"""
    try:
        # 설정 파일 로드
        config_path = project_root / "config.yaml"
        if not config_path.exists():
            logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 카카오 계정 정보 확인
        tistory_config = config.get('tistory', {})
        browser_auth_config = config.get('browser_auth', {})
        
        kakao_email = browser_auth_config.get('kakao_email')
        kakao_password = browser_auth_config.get('kakao_password')
        
        if not kakao_email or not kakao_password:
            logger.error("카카오 계정 정보가 설정되지 않았습니다.")
            logger.error("config.yaml에 다음 설정을 추가하세요:")
            logger.error("""
browser_auth:
  kakao_email: "your_kakao_email@example.com"
  kakao_password: "your_kakao_password"
  headless: false  # 처음 설정 시 false 권장 (수동 인증 필요 시)
            """)
            return
        
        # 쿠키 저장 파일 경로
        cookie_file = project_root / "data" / "cookies.json"
        headless = browser_auth_config.get('headless', True)
        
        logger.info("=" * 70)
        logger.info("쿠키 갱신 시작 (브라우저 자동화)")
        logger.info("=" * 70)
        
        # 브라우저 인증 시작
        with BrowserAuth(headless=headless, cookie_file=str(cookie_file)) as auth:
            # 카카오 로그인
            cookies = auth.login_with_kakao(kakao_email, kakao_password)
            
            if cookies:
                logger.info("=" * 70)
                logger.info("✅ 쿠키 갱신 성공!")
                logger.info("=" * 70)
                logger.info("다음 단계:")
                logger.info("1. config.yaml 파일 열기")
                logger.info("2. tistory.cookies에 다음 쿠키 업데이트:")
                logger.info("")
                logger.info(f"   cookies: \"{cookies}\"")
                logger.info("")
                logger.info("3. 프로그램 재시작")
                logger.info("=" * 70)
            else:
                logger.error("쿠키 갱신 실패")
                logger.error("카카오 계정 정보를 확인하거나 headless: false로 설정하여 수동 인증을 시도하세요.")
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)


if __name__ == "__main__":
    main()

