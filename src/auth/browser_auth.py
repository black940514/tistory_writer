"""
브라우저 자동화를 통한 티스토리 카카오 로그인 및 쿠키 관리
"""
import logging
import time
import json
import os
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Selenium 가용성 확인
SELENIUM_AVAILABLE = True
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    try:
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        ChromeDriverManager = None
except ImportError:
    SELENIUM_AVAILABLE = False


class BrowserAuth:
    """브라우저 자동화를 통한 카카오 로그인 및 쿠키 관리"""
    
    TISTORY_LOGIN_URL = "https://www.tistory.com/auth/login"
    TISTORY_BASE_URL = "https://www.tistory.com"
    
    def __init__(self, headless: bool = True, cookie_file: Optional[str] = None):
        """
        브라우저 인증 초기화
        
        Args:
            headless: 헤드리스 모드 (True: 브라우저 창 안 띄움, False: 브라우저 창 띄움)
            cookie_file: 쿠키 저장 파일 경로 (선택적)
        """
        self.headless = headless
        self.cookie_file = Path(cookie_file) if cookie_file else None
        self.driver = None
    
    def _init_driver(self):
        """Selenium WebDriver 초기화"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium이 설치되지 않았습니다. pip install selenium webdriver-manager를 실행하세요.")
        
        # HOME 환경 변수 설정 (함수 시작 부분에 먼저 설정)
        # webdriver-manager가 사용하기 전에 설정해야 함
        if os.environ.get('HOME') == '/nonexistent' or not os.path.exists(os.environ.get('HOME', '')):
            os.environ['HOME'] = '/app'
        
        # Selenium cache 경로 설정 (권한 문제 해결)
        # Docker 환경에서 /nonexistent 홈 디렉토리 문제 해결
        cache_dir = os.environ.get('SELENIUM_CACHE_DIR', '/app/.cache/selenium')
        home_dir = os.environ.get('HOME', '/app')
        
        # Selenium 캐시 디렉토리 생성 (권한 문제 해결을 위해 777로 설정)
        try:
            os.makedirs(cache_dir, exist_ok=True)
            os.makedirs(f'{cache_dir}/chrome', exist_ok=True)
            os.makedirs(f'{home_dir}/.cache/selenium', exist_ok=True)
            # 권한 설정 (Docker 환경에서 권한 문제 해결)
            os.chmod(cache_dir, 0o777)
            os.chmod(f'{cache_dir}/chrome', 0o777)
            if os.path.exists(f'{home_dir}/.cache'):
                os.chmod(f'{home_dir}/.cache', 0o777)
            if os.path.exists(f'{home_dir}/.cache/selenium'):
                os.chmod(f'{home_dir}/.cache/selenium', 0o777)
        except Exception as e:
            logger.warning(f"Selenium cache 디렉토리 생성 실패 (무시): {e}")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless=new')  # 새로운 headless 모드
        
        # Docker 환경에서 Chrome 실행에 필요한 옵션 (X11 디스플레이 문제 해결)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        # X11 디스플레이 문제 해결
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        # Ozone 플랫폼 설정 (X11 대신 headless 사용)
        chrome_options.add_argument('--use-gl=swiftshader')
        chrome_options.add_argument('--enable-features=UseOzonePlatform')
        chrome_options.add_argument('--ozone-platform=headless')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
        
        # Chrome user data 디렉토리 설정 (임시 디렉토리 사용)
        # user-data-dir을 사용하면 권한 문제가 발생할 수 있으므로 임시 디렉토리 사용
        import tempfile
        temp_user_data_dir = tempfile.mkdtemp(prefix='chrome_user_data_')
        chrome_options.add_argument(f'--user-data-dir={temp_user_data_dir}')
        logger.debug(f"Chrome user-data-dir: {temp_user_data_dir}")
        
        # 자동화 감지 방지
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Chrome 브라우저 실행 경로 찾기
            chrome_binary_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium'
            ]
            chrome_binary = None
            for path in chrome_binary_paths:
                if os.path.exists(path):
                    chrome_binary = path
                    break
            
            if chrome_binary:
                chrome_options.binary_location = chrome_binary
                logger.info(f"Chrome 브라우저 경로 지정: {chrome_binary}")
                
                # Chrome 버전 확인
                try:
                    import subprocess
                    chrome_version = subprocess.check_output([chrome_binary, '--version'], stderr=subprocess.STDOUT).decode().strip()
                    logger.info(f"Chrome 버전: {chrome_version}")
                except Exception as e:
                    logger.debug(f"Chrome 버전 확인 실패: {e}")
            else:
                logger.warning("Chrome 브라우저 실행 파일을 찾을 수 없습니다. 기본 경로를 사용합니다.")
            
            # ChromeDriver 경로 확인
            chromedriver_paths = [
                '/usr/local/bin/chromedriver',
                '/usr/bin/chromedriver',
                '/app/.cache/selenium/chromedriver'
            ]
            chromedriver_path = None
            for path in chromedriver_paths:
                if os.path.exists(path):
                    chromedriver_path = path
                    break
            
            # Selenium Service를 사용하여 ChromeDriver 경로 명시적 지정
            from selenium.webdriver.chrome.service import Service
            
            if chromedriver_path:
                logger.info(f"ChromeDriver 경로 지정: {chromedriver_path}")
                
                # ChromeDriver 버전 확인
                try:
                    import subprocess
                    chromedriver_version = subprocess.check_output([chromedriver_path, '--version'], stderr=subprocess.STDOUT).decode().strip()
                    logger.info(f"ChromeDriver 버전: {chromedriver_version}")
                except Exception as e:
                    logger.warning(f"ChromeDriver 버전 확인 실패: {e}")
                
                # ChromeDriver Service 설정
                service = Service(chromedriver_path)
                # 로그 출력 활성화 (디버깅용) - stdout으로 출력
                import sys
                service.log_output = sys.stdout
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                logger.info("ChromeDriver 경로를 찾을 수 없습니다. Selenium이 자동으로 관리하도록 시도합니다.")
                # ChromeDriver가 없으면 Selenium 4.15+가 자동으로 관리 시도
                self.driver = webdriver.Chrome(options=chrome_options)
            
            # 자동화 감지 스크립트 제거
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            logger.info("Chrome WebDriver 초기화 완료")
        except Exception as e:
            logger.error(f"WebDriver 초기화 실패: {e}")
            logger.error("Chrome 브라우저가 설치되어 있는지 확인하세요.")
            if 'chrome_binary' in locals() and chrome_binary:
                logger.error(f"시도한 Chrome 실행 파일 경로: {chrome_binary}")
            if 'chromedriver_path' in locals() and chromedriver_path:
                logger.error(f"시도한 ChromeDriver 경로: {chromedriver_path}")
            
            # ChromeDriver 로그 파일 확인
            chromedriver_log_path = '/app/data/chromedriver.log'
            if os.path.exists(chromedriver_log_path):
                try:
                    with open(chromedriver_log_path, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                        if log_content:
                            logger.error("ChromeDriver 로그 (마지막 1000자):")
                            logger.error(log_content[-1000:])
                except Exception as log_err:
                    logger.debug(f"ChromeDriver 로그 읽기 실패: {log_err}")
            
            # 더 자세한 디버깅 정보
            logger.debug("디버깅 정보:", exc_info=True)
            raise
    
    def login_with_kakao(self, kakao_email: str, kakao_password: str, timeout: int = 60) -> Optional[str]:
        """
        카카오 계정으로 티스토리 로그인
        
        Args:
            kakao_email: 카카오 계정 이메일
            kakao_password: 카카오 계정 비밀번호
            timeout: 타임아웃 (초)
        
        Returns:
            쿠키 문자열 또는 None (실패 시)
        """
        try:
            if not self.driver:
                self._init_driver()
            
            logger.info("티스토리 로그인 페이지 접근 중...")
            self.driver.get(self.TISTORY_LOGIN_URL)
            time.sleep(2)
            
            # 카카오 로그인 버튼 찾기
            try:
                # 다양한 선택자로 카카오 로그인 버튼 찾기
                kakao_button = None
                kakao_href = None  # href를 즉시 저장
                used_selector = None
                selectors = [
                    "a[href*='kakao']",
                    "button[class*='kakao']",
                    "a[class*='kakao']",
                    "//a[contains(text(), '카카오')]",
                    "//button[contains(text(), '카카오')]",
                    "//a[contains(@href, 'kakao')]"
                ]

                for selector in selectors:
                    try:
                        if selector.startswith("//"):
                            kakao_button = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, selector))
                            )
                        else:
                            kakao_button = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                        if kakao_button:
                            # 버튼을 찾은 즉시 href 속성을 저장 (stale element 방지)
                            try:
                                kakao_href = kakao_button.get_attribute('href')
                            except:
                                pass
                            used_selector = selector
                            logger.info(f"카카오 로그인 버튼 발견: {selector}")
                            if kakao_href:
                                logger.info(f"카카오 로그인 URL 저장됨: {kakao_href[:50]}...")
                            break
                    except (NoSuchElementException, TimeoutException):
                        continue

                if not kakao_button:
                    logger.error("카카오 로그인 버튼을 찾을 수 없습니다.")
                    logger.error("페이지 소스 일부를 확인합니다...")
                    logger.debug(self.driver.page_source[:500])
                    return None

                # 클릭 시도 (href가 있으면 직접 이동 우선)
                clicked = False

                # 방법 1: 저장된 href로 직접 이동 (가장 안정적)
                if kakao_href:
                    try:
                        logger.info(f"저장된 href로 직접 이동: {kakao_href[:50]}...")
                        self.driver.get(kakao_href)
                        clicked = True
                        logger.info("href 직접 이동 성공")
                    except Exception as href_error:
                        logger.warning(f"href 직접 이동 실패: {href_error}")

                # 방법 2: 요소 다시 찾아서 클릭
                if not clicked:
                    try:
                        # 요소를 다시 찾기 (stale element 방지)
                        if used_selector.startswith("//"):
                            fresh_button = self.driver.find_element(By.XPATH, used_selector)
                        else:
                            fresh_button = self.driver.find_element(By.CSS_SELECTOR, used_selector)
                        fresh_button.click()
                        clicked = True
                        logger.info("요소 재탐색 후 클릭 성공")
                    except Exception as e:
                        logger.warning(f"요소 재탐색 클릭 실패: {e}")

                # 방법 3: JavaScript 클릭
                if not clicked:
                    try:
                        if used_selector.startswith("//"):
                            fresh_button = self.driver.find_element(By.XPATH, used_selector)
                        else:
                            fresh_button = self.driver.find_element(By.CSS_SELECTOR, used_selector)
                        self.driver.execute_script("arguments[0].click();", fresh_button)
                        clicked = True
                        logger.info("JavaScript 클릭 성공")
                    except Exception as js_error:
                        logger.warning(f"JavaScript 클릭 실패: {js_error}")

                if not clicked:
                    logger.error("카카오 로그인 버튼 클릭 실패 (모든 방법 시도됨)")
                    return None
                
                logger.info("카카오 로그인 페이지로 이동 중...")
                # 페이지 로딩 대기
                time.sleep(5)
                
                # 현재 URL 확인
                current_url = self.driver.current_url
                logger.info(f"현재 URL: {current_url}")
                
                # #kakaoBody 프래그먼트가 있는 경우, 카카오 로그인 링크를 한 번 더 클릭
                if '#kakaoBody' in current_url or 'kakaoBody' in current_url:
                    logger.info("#kakaoBody 프래그먼트 감지 - 카카오 로그인 링크를 다시 클릭합니다.")
                    time.sleep(3)  # 페이지 로딩 대기
                    
                    # 카카오 로그인 링크/버튼 다시 찾기
                    kakao_link_selectors = [
                        "a[href*='kakao']",
                        "a[href*='kauth.kakao.com']",
                        "a[href*='accounts.kakao.com']",
                        "button[class*='kakao']",
                        "a[class*='kakao']",
                        "//a[contains(text(), '카카오')]",
                        "//button[contains(text(), '카카오')]",
                        "#kakaoBody a",
                        "[id*='kakao'] a",
                    ]
                    
                    kakao_link_clicked = False
                    wait = WebDriverWait(self.driver, 10)
                    for selector in kakao_link_selectors:
                        try:
                            if selector.startswith("//"):
                                elements = self.driver.find_elements(By.XPATH, selector)
                            else:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            for element in elements:
                                try:
                                    if element.is_displayed() and element.is_enabled():
                                        logger.info(f"카카오 로그인 링크 발견 (재클릭): {selector}")
                                        # JavaScript로 클릭 시도
                                        self.driver.execute_script("arguments[0].click();", element)
                                        kakao_link_clicked = True
                                        logger.info("카카오 로그인 링크 클릭 완료")
                                        break
                                except Exception as e:
                                    logger.debug(f"요소 클릭 실패: {e}")
                                    continue
                            
                            if kakao_link_clicked:
                                break
                        except Exception as e:
                            logger.debug(f"카카오 링크 찾기 실패 ({selector}): {e}")
                            continue
                    
                    if kakao_link_clicked:
                        logger.info("카카오 로그인 페이지 로딩 대기 중...")
                        time.sleep(5)  # 페이지 로딩 대기
                        
                        # URL 변경 확인
                        new_url = self.driver.current_url
                        logger.info(f"클릭 후 URL: {new_url}")
                
                # 카카오 로그인 페이지가 로드될 때까지 대기
                wait = WebDriverWait(self.driver, 20)
                try:
                    # 페이지가 로드되었는지 확인
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    logger.info("페이지 로딩 완료")
                    
                    # 최종 URL 확인
                    final_url = self.driver.current_url
                    logger.info(f"최종 URL: {final_url}")
                    
                    # 카카오 로그인 페이지로 리다이렉트되었는지 확인
                    if 'accounts.kakao.com' in final_url or 'kauth.kakao.com' in final_url:
                        logger.info("카카오 로그인 페이지로 리다이렉트됨")
                    else:
                        logger.info(f"현재 페이지에서 로그인 폼 찾기 (URL: {final_url})")
                except TimeoutException:
                    logger.warning("페이지 로딩 타임아웃")
                
            except Exception as e:
                logger.error(f"카카오 로그인 버튼 클릭 실패: {e}")
                return None
            
            # 카카오 로그인 페이지에서 이메일/비밀번호 입력
            try:
                # 현재 URL 확인 (카카오 로그인 페이지로 리다이렉트되었는지)
                current_url = self.driver.current_url
                logger.info(f"로그인 폼 찾기 전 현재 URL: {current_url}")
                
                # iframe 처리: iframe이 있는지 확인하고 전환
                iframe_found = False
                try:
                    # iframe 찾기 (여러 방법 시도)
                    iframe_selectors = [
                        "iframe[id*='kakao']",
                        "iframe[src*='kakao']",
                        "iframe[src*='kauth']",
                        "iframe[src*='accounts.kakao']",
                        "iframe.kakao",
                        "iframe#kakaoBody",
                        "iframe",
                    ]
                    
                    wait = WebDriverWait(self.driver, 10)
                    for iframe_selector in iframe_selectors:
                        try:
                            iframes = self.driver.find_elements(By.CSS_SELECTOR, iframe_selector)
                            for iframe in iframes:
                                try:
                                    # iframe으로 전환
                                    self.driver.switch_to.frame(iframe)
                                    logger.info(f"iframe으로 전환: {iframe_selector}")
                                    iframe_found = True
                                    
                                    # iframe 내부에서 페이지 로딩 대기
                                    time.sleep(3)
                                    break
                                except Exception as e:
                                    logger.debug(f"iframe 전환 실패: {e}")
                                    continue
                            if iframe_found:
                                break
                        except Exception as e:
                            logger.debug(f"iframe 찾기 실패 ({iframe_selector}): {e}")
                            continue
                    
                    if not iframe_found:
                        logger.info("iframe을 찾을 수 없습니다. 메인 페이지에서 검색합니다.")
                except Exception as e:
                    logger.debug(f"iframe 처리 중 오류 (무시하고 계속): {e}")
                
                # 이메일 입력 필드 찾기 (더 많은 선택자 시도)
                email_selectors = [
                    "input[id='loginKey--1']",
                    "input[id*='loginKey']",
                    "input[name='email']",
                    "input[name='loginKey']",
                    "input[type='email']",
                    "input[type='text']",
                    "input[placeholder*='이메일']",
                    "input[placeholder*='카카오계정']",
                    "input[placeholder*='email']",
                    "input[placeholder*='Email']",
                    "#loginKey--1",
                    "input.input_text",
                    "input.form_input",
                    "input[class*='input']",
                    "input[class*='text']",
                ]
                
                email_input = None
                wait = WebDriverWait(self.driver, 15)
                for selector in email_selectors:
                    try:
                        logger.debug(f"이메일 필드 찾기 시도: {selector}")
                        email_input = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        if email_input:
                            # 요소가 표시되고 활성화되어 있는지 확인
                            if email_input.is_displayed() and email_input.is_enabled():
                                logger.info(f"이메일 입력 필드 발견: {selector}")
                                break
                            else:
                                email_input = None
                    except (TimeoutException, NoSuchElementException):
                        continue
                
                if not email_input:
                    logger.error("이메일 입력 필드를 찾을 수 없습니다.")
                    # 페이지 스크린샷 저장 시도 (디버깅용, headless 모드에서는 작동하지 않을 수 있음)
                    try:
                        self.driver.save_screenshot("/tmp/kakao_login_page.png")
                        logger.info("페이지 스크린샷 저장: /tmp/kakao_login_page.png")
                    except:
                        pass
                    # iframe 내부였다면 메인 페이지로 돌아가서 다시 시도
                    try:
                        if iframe_found:
                            logger.info("iframe 내부에서 찾지 못했으므로 메인 페이지로 돌아가 다시 시도합니다.")
                            self.driver.switch_to.default_content()
                            time.sleep(2)
                            
                            # 메인 페이지에서 다시 시도
                            for selector in email_selectors[:5]:  # 주요 선택자만 시도
                                try:
                                    email_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if email_input and email_input.is_displayed() and email_input.is_enabled():
                                        logger.info(f"메인 페이지에서 이메일 입력 필드 발견: {selector}")
                                        break
                                except:
                                    continue
                    except Exception as e:
                        logger.debug(f"메인 페이지로 돌아가기 실패: {e}")
                    
                    if not email_input:
                        # 페이지 소스의 input 태그들 확인
                        try:
                            inputs = self.driver.find_elements(By.TAG_NAME, "input")
                            logger.info(f"페이지에 {len(inputs)}개의 input 요소가 있습니다:")
                            for i, inp in enumerate(inputs[:10]):  # 최대 10개만
                                try:
                                    logger.info(f"  Input {i}: id={inp.get_attribute('id')}, name={inp.get_attribute('name')}, type={inp.get_attribute('type')}, placeholder={inp.get_attribute('placeholder')}, displayed={inp.is_displayed()}")
                                except:
                                    pass
                        except:
                            pass
                        return None
                
                email_input.clear()
                email_input.send_keys(kakao_email)
                logger.info("이메일 입력 완료")
                time.sleep(1)

                # 카카오 2단계 로그인: "다음" 또는 "계속" 버튼 클릭 (비밀번호 필드가 바로 없는 경우)
                next_button_selectors = [
                    "button[type='submit']",
                    "button[class*='submit']",
                    "button[class*='next']",
                    "button[class*='continue']",
                    "//button[contains(text(), '다음')]",
                    "//button[contains(text(), '계속')]",
                    "//button[contains(text(), '확인')]",
                ]

                # 먼저 비밀번호 필드가 이미 있는지 확인
                password_input = None
                password_selectors = [
                    "input[id='password--2']",
                    "input[name='password']",
                    "input[type='password']",
                    "input[placeholder*='비밀번호']"
                ]

                for selector in password_selectors:
                    try:
                        password_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if password_input and password_input.is_displayed():
                            logger.info("비밀번호 필드가 이미 표시되어 있습니다.")
                            break
                        else:
                            password_input = None
                    except NoSuchElementException:
                        continue

                # 비밀번호 필드가 없으면 "다음" 버튼 클릭
                if not password_input:
                    logger.info("비밀번호 필드가 없음 - '다음' 버튼 클릭 시도...")
                    next_button = None
                    for selector in next_button_selectors:
                        try:
                            if selector.startswith("//"):
                                next_button = self.driver.find_element(By.XPATH, selector)
                            else:
                                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if next_button and next_button.is_displayed():
                                break
                            else:
                                next_button = None
                        except NoSuchElementException:
                            continue

                    if next_button:
                        try:
                            next_button.click()
                            logger.info("'다음' 버튼 클릭 완료")
                        except:
                            self.driver.execute_script("arguments[0].click();", next_button)
                            logger.info("'다음' 버튼 JavaScript 클릭 완료")
                        time.sleep(3)  # 페이지 전환 대기

                    # 비밀번호 필드 다시 찾기 (최대 10초 대기)
                    wait = WebDriverWait(self.driver, 10)
                    for selector in password_selectors:
                        try:
                            password_input = wait.until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            if password_input and password_input.is_displayed():
                                logger.info(f"비밀번호 필드 발견: {selector}")
                                break
                            else:
                                password_input = None
                        except (TimeoutException, NoSuchElementException):
                            continue

                if not password_input:
                    logger.error("비밀번호 입력 필드를 찾을 수 없습니다.")
                    # 현재 페이지 input 요소들 확인
                    try:
                        inputs = self.driver.find_elements(By.TAG_NAME, "input")
                        logger.info(f"페이지에 {len(inputs)}개의 input 요소:")
                        for i, inp in enumerate(inputs[:5]):
                            logger.info(f"  Input {i}: type={inp.get_attribute('type')}, name={inp.get_attribute('name')}, displayed={inp.is_displayed()}")
                    except:
                        pass
                    return None

                password_input.clear()
                password_input.send_keys(kakao_password)
                logger.info("비밀번호 입력 완료")
                time.sleep(1)
                
                # 로그인 버튼 클릭
                login_button_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button[class*='login']",
                    "//button[contains(text(), '로그인')]",
                    "//input[@value='로그인']"
                ]
                
                login_button = None
                for selector in login_button_selectors:
                    try:
                        if selector.startswith("//"):
                            login_button = self.driver.find_element(By.XPATH, selector)
                        else:
                            login_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if login_button:
                            break
                    except NoSuchElementException:
                        continue
                
                if not login_button:
                    logger.error("로그인 버튼을 찾을 수 없습니다.")
                    return None
                
                login_button.click()
                logger.info("로그인 버튼 클릭 완료")
                time.sleep(5)
                
                # 추가 인증 (2단계 인증, OAuth 동의 등) 확인 및 대기
                current_url = self.driver.current_url
                if 'login' in current_url.lower() or 'auth' in current_url.lower() or 'kauth' in current_url.lower():
                    logger.warning("로그인 후에도 인증 페이지에 머물러 있습니다.")
                    logger.warning("2단계 인증이나 OAuth 동의가 필요할 수 있습니다.")
                    logger.warning("현재 URL: " + current_url)

                    # 폴링으로 URL 변경 감지 및 자동 처리 (최대 120초)
                    max_wait = 120
                    poll_interval = 2
                    waited = 0

                    if not self.headless:
                        logger.info("브라우저 창에서 수동으로 인증을 완료해주세요...")
                        logger.info("또는 자동으로 동의 버튼을 클릭합니다.")

                    while waited < max_wait:
                        time.sleep(poll_interval)
                        waited += poll_interval
                        check_url = self.driver.current_url

                        # 티스토리로 리다이렉트 완료
                        if 'tistory.com' in check_url and 'login' not in check_url.lower():
                            logger.info(f"인증 완료 감지! ({waited}초 후)")
                            break

                        # OAuth 동의 페이지 처리 (kauth.kakao.com/oauth/authorize)
                        if 'kauth.kakao.com' in check_url and 'authorize' in check_url:
                            logger.info("OAuth 동의 페이지 감지 - 동의 버튼 클릭 시도...")
                            consent_selectors = [
                                "button[type='submit']",
                                "button.confirm",
                                "//button[contains(text(), '동의')]",
                                "//button[contains(text(), '계속')]",
                                "//button[contains(text(), '확인')]",
                                "//button[contains(text(), '허용')]",
                                "button[class*='agree']",
                                "button[class*='consent']",
                            ]
                            for selector in consent_selectors:
                                try:
                                    if selector.startswith("//"):
                                        consent_btn = self.driver.find_element(By.XPATH, selector)
                                    else:
                                        consent_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if consent_btn and consent_btn.is_displayed():
                                        self.driver.execute_script("arguments[0].click();", consent_btn)
                                        logger.info(f"동의 버튼 클릭 완료: {selector}")
                                        time.sleep(3)
                                        break
                                except:
                                    continue

                        if waited % 10 == 0:
                            logger.info(f"대기 중... ({waited}초/{max_wait}초)")

                # 티스토리 메인 페이지로 리다이렉트 확인
                final_url = self.driver.current_url
                logger.info(f"최종 URL: {final_url}")

                if 'tistory.com' in final_url and 'login' not in final_url:
                    logger.info("로그인 성공!")
                    # 쿠키 추출
                    cookies = self._extract_cookies()
                    return cookies
                else:
                    logger.error("로그인 실패 또는 인증이 완료되지 않았습니다.")
                    logger.error("카카오 계정 보안 설정에서 2단계 인증을 확인하세요.")
                    return None
                    
            except Exception as e:
                logger.error(f"카카오 로그인 과정 중 오류: {e}", exc_info=True)
                return None
                
        except Exception as e:
            logger.error(f"로그인 프로세스 오류: {e}", exc_info=True)
            return None
    
    def _extract_cookies(self) -> str:
        """현재 브라우저 세션의 쿠키 추출"""
        cookies = self.driver.get_cookies()
        
        # 중요한 쿠키만 필터링
        important_cookies = ['TSSESSION', '_T_ANO', 'TOP-XSRF-TOKEN', 'JSESSIONID', 'TISTORY']
        cookie_pairs = []
        
        for cookie in cookies:
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            if name in important_cookies or any(important in name.upper() for important in important_cookies):
                cookie_pairs.append(f"{name}={value}")
        
        cookie_string = "; ".join(cookie_pairs)
        logger.info(f"쿠키 추출 완료: {len(cookie_pairs)}개")
        return cookie_string
    
    def refresh_cookies(self, kakao_email: str, kakao_password: str) -> Optional[str]:
        """
        쿠키 갱신 (재로그인)
        
        Args:
            kakao_email: 카카오 계정 이메일
            kakao_password: 카카오 계정 비밀번호
        
        Returns:
            갱신된 쿠키 문자열
        """
        logger.info("쿠키 갱신을 위해 재로그인 중...")
        cookies = self.login_with_kakao(kakao_email, kakao_password)
        
        if cookies and self.cookie_file:
            self._save_cookies_to_file(cookies)
        
        return cookies
    
    def _save_cookies_to_file(self, cookies: str):
        """쿠키를 파일에 저장"""
        try:
            cookie_data = {
                'cookies': cookies,
                'updated_at': datetime.now().isoformat()
            }
            
            self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"쿠키가 파일에 저장되었습니다: {self.cookie_file}")
        except Exception as e:
            logger.error(f"쿠키 파일 저장 실패: {e}")
    
    def _load_cookies_from_file(self) -> Optional[str]:
        """파일에서 쿠키 로드"""
        if not self.cookie_file or not self.cookie_file.exists():
            return None
        
        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('cookies')
        except Exception as e:
            logger.error(f"쿠키 파일 로드 실패: {e}")
            return None
    
    def verify_login(self) -> bool:
        """현재 세션이 로그인되어 있는지 확인"""
        try:
            if not self.driver:
                self._init_driver()
            
            self.driver.get(f"{self.TISTORY_BASE_URL}/manage/posts")
            time.sleep(2)
            
            current_url = self.driver.current_url
            if 'login' in current_url.lower():
                return False
            
            # 로그아웃 버튼이나 관리 메뉴 확인
            page_source = self.driver.page_source.lower()
            if '로그아웃' in page_source or 'logout' in page_source:
                return True
            
            return False
        except Exception as e:
            logger.error(f"로그인 상태 확인 실패: {e}")
            return False
    
    def close(self):
        """브라우저 종료"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("브라우저 종료 완료")
            except:
                pass
            self.driver = None
    
    def __enter__(self):
        """Context manager 진입"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.close()

