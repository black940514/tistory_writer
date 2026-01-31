"""
쿠키 갱신 유틸리티 (주기적으로 쿠키 갱신)
"""
import logging
import yaml
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    from ..auth.browser_auth import BrowserAuth, SELENIUM_AVAILABLE
except ImportError:
    SELENIUM_AVAILABLE = False


class CookieRefresher:
    """쿠키 갱신 관리자"""
    
    def __init__(self, config_path: str, cookie_file: Optional[str] = None):
        """
        쿠키 갱신 관리자 초기화
        
        Args:
            config_path: config.yaml 파일 경로
            cookie_file: 쿠키 저장 파일 경로 (선택적)
        """
        self.config_path = Path(config_path)
        self.cookie_file = Path(cookie_file) if cookie_file else Path(config_path).parent / "data" / "cookies.json"
        
    def load_config(self) -> dict:
        """설정 파일 로드"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def save_cookies_to_config(self, cookies: str):
        """쿠키를 config.yaml에 저장"""
        try:
            # 설정 파일 읽기
            config = self.load_config()
            
            # 쿠키 업데이트
            if 'tistory' not in config:
                config['tistory'] = {}
            
            config['tistory']['cookies'] = cookies
            
            # 설정 파일 저장
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            logger.info(f"쿠키가 config.yaml에 저장되었습니다: {self.config_path}")
        except Exception as e:
            logger.error(f"config.yaml 쿠키 저장 실패: {e}")
            raise
    
    def refresh_cookies_if_needed(self, force: bool = False) -> bool:
        """
        필요시 쿠키 갱신
        
        Args:
            force: 강제 갱신 (기본값: False, 자동 판단)
        
        Returns:
            갱신 성공 여부
        """
        if not SELENIUM_AVAILABLE:
            logger.warning("Selenium이 설치되지 않아 쿠키 자동 갱신을 사용할 수 없습니다.")
            return False
        
        try:
            config = self.load_config()
            browser_auth_config = config.get('browser_auth', {})
            
            kakao_email = browser_auth_config.get('kakao_email')
            kakao_password = browser_auth_config.get('kakao_password')
            
            if not kakao_email or not kakao_password:
                logger.debug("카카오 계정 정보가 설정되지 않아 쿠키 자동 갱신을 건너뜁니다.")
                return False
            
            # 강제 갱신이 아니면 마지막 갱신 시간 확인
            if not force and self.cookie_file.exists():
                try:
                    import json
                    with open(self.cookie_file, 'r', encoding='utf-8') as f:
                        cookie_data = json.load(f)
                    updated_at_str = cookie_data.get('updated_at')
                    if updated_at_str:
                        updated_at = datetime.fromisoformat(updated_at_str)
                        age = datetime.now() - updated_at
                        # 7일 이상 지났을 때만 갱신
                        if age.days < 7:
                            logger.debug(f"쿠키가 아직 유효합니다 ({age.days}일 경과). 갱신 건너뜁니다.")
                            return True
                except Exception as e:
                    logger.debug(f"쿠키 파일 확인 중 오류: {e}")
            
            # 쿠키 갱신
            headless = browser_auth_config.get('headless', True)
            
            logger.info("쿠키 자동 갱신 시작...")
            with BrowserAuth(headless=headless, cookie_file=str(self.cookie_file)) as auth:
                cookies = auth.refresh_cookies(kakao_email, kakao_password)
                
                if cookies:
                    # config.yaml에 쿠키 저장
                    self.save_cookies_to_config(cookies)
                    logger.info("✅ 쿠키 갱신 완료!")
                    return True
                else:
                    logger.error("쿠키 갱신 실패")
                    return False
                    
        except Exception as e:
            logger.error(f"쿠키 갱신 중 오류: {e}", exc_info=True)
            return False

