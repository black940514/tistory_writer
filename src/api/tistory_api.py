"""
티스토리 웹 인터페이스 클라이언트 (API 없이 HTTP Request 사용)
"""
import requests
from http.cookiejar import Cookie
import logging
import re
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class TistoryAPI:
    """티스토리 웹 인터페이스 클라이언트 (세션 기반)"""
    
    BASE_URL = "https://www.tistory.com"
    
    def __init__(self, user_id: str = None, user_pw: str = None, blog_name: str = None, cookies: str = None, blog_id: str = None):
        """
        티스토리 API 클라이언트 초기화
        
        Args:
            user_id: 티스토리 로그인 ID (선택, cookies 사용 시 불필요)
            user_pw: 티스토리 로그인 비밀번호 (선택, cookies 사용 시 불필요)
            blog_name: 블로그 이름 (예: example.tistory.com의 example)
            cookies: 세션 쿠키 문자열 (카카오 로그인 시 권장, 브라우저에서 추출)
            blog_id: 블로그 ID (선택적, 글쓰기 페이지 URL에서 확인)
        
        Note:
            - 카카오 로그인 사용 시 cookies 방식 권장
            - blog_id는 글쓰기 페이지 URL에서 확인 가능 (예: /manage/newpost/99 → "99")
        """
        self.user_id = user_id
        self.user_pw = user_pw
        self.blog_name = blog_name
        self.blog_id = blog_id  # 블로그 ID (예: 99)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        if cookies:
            # 쿠키 문자열을 파싱하여 세션에 추가 (카카오 로그인 시 사용)
            self._set_cookies(cookies)
            logger.info("쿠키를 사용하여 세션 설정 (카카오 로그인 또는 세션 쿠키)")
            # 로그인 상태 확인
            self._verify_login()
        elif user_id and user_pw:
            logger.info("ID/비밀번호로 로그인 시도")
            self._login()
        else:
            raise ValueError("cookies 또는 user_id/user_pw 중 하나는 필수입니다. (카카오 로그인 시에는 cookies 사용 권장)")
    
    def _set_cookies(self, cookies_str: str):
        """쿠키 문자열을 세션에 설정 (카카오 로그인 시 사용)"""
        # 쿠키 파싱 (예: "JSESSIONID=xxx; TISTORY=yyy; TSSESSION=zzz")
        cookie_count = 0
        important_cookies = []
        
        # 인증 관련 쿠키 이름 목록 (대소문자 구분 없이)
        auth_cookie_names = [
            'JSESSIONID', 'TISTORY', 'SESSIONID', 'SESSION',
            'TSSESSION', '_T_ANO', 'TOP-XSRF-TOKEN', 'XSRF-TOKEN'
        ]
        
        for cookie in cookies_str.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                name, value = cookie.split('=', 1)
                name = name.strip()
                value = value.strip()
                
                # 중요 쿠키 확인
                if name.upper() in [n.upper() for n in auth_cookie_names]:
                    important_cookies.append(name)
                
                # 쿠키 도메인 결정
                # www.tistory.com 쿠키는 www.tistory.com에, 나머지는 .tistory.com에 설정
                if name == 'TOP-XSRF-TOKEN':
                    domain = 'www.tistory.com'
                    # Cookie 객체를 직접 생성하여 추가
                    cookie_obj = Cookie(
                        version=0, name=name, value=value,
                        port=None, port_specified=False,
                        domain=domain, domain_specified=True, domain_initial_dot=False,
                        path='/', path_specified=True,
                        secure=False, expires=None, discard=True,
                        comment=None, comment_url=None,
                        rest={}, rfc2109=False
                    )
                    self.session.cookies.set_cookie(cookie_obj)
                else:
                    # .tistory.com 도메인에 쿠키 설정 (하위 도메인 포함)
                    domain = '.tistory.com'
                    cookie_obj = Cookie(
                        version=0, name=name, value=value,
                        port=None, port_specified=False,
                        domain=domain, domain_specified=True, domain_initial_dot=True,
                        path='/', path_specified=True,
                        secure=False, expires=None, discard=True,
                        comment=None, comment_url=None,
                        rest={}, rfc2109=False
                    )
                    self.session.cookies.set_cookie(cookie_obj)
                cookie_count += 1
        
        logger.info(f"{cookie_count}개의 쿠키 설정 완료")
        if important_cookies:
            logger.info(f"인증 쿠키 확인됨: {', '.join(important_cookies)}")
        else:
            logger.warning("인증 쿠키(TSSESSION, _T_ANO, JSESSIONID, TISTORY 등)를 찾을 수 없습니다.")
    
    def _verify_login(self):
        """로그인 상태 확인"""
        try:
            # 메인 페이지 접근하여 로그인 상태 확인
            test_url = f"{self.BASE_URL}/"
            response = self.session.get(test_url, allow_redirects=True)
            
            # 최종 URL 확인
            final_url = response.url
            
            # 로그인 페이지로 리다이렉트된 경우
            if '/login' in final_url or '/auth/login' in final_url:
                logger.error("로그인 상태 확인 실패: 로그인 페이지로 리다이렉트됨")
                logger.error("쿠키가 만료되었거나 잘못된 쿠키입니다. 새로 추출해주세요.")
                raise Exception("쿠키가 유효하지 않습니다. 브라우저에서 다시 로그인하여 쿠키를 추출해주세요.")
            
            # 로그아웃 버튼이나 관리 메뉴가 있는지 확인
            if response.status_code == 200:
                # 여러 방법으로 로그인 상태 확인
                text_lower = response.text.lower()
                login_indicators = [
                    '로그아웃' in response.text,
                    'logout' in text_lower,
                    '관리' in response.text,
                    '/manage/' in final_url,  # 관리 페이지 URL
                    'newpost' in text_lower,  # 글쓰기 링크
                    'tistory.com/manage' in final_url  # 관리 페이지 경로
                ]
                
                if any(login_indicators):
                    logger.info("로그인 상태 확인 완료: 정상적으로 로그인되어 있습니다.")
                else:
                    # 컨테이너 환경에서는 HTML 구조가 다를 수 있으므로 경고만 출력
                    logger.warning("로그인 상태를 명확히 확인할 수 없지만 계속 진행합니다. (컨테이너 환경에서는 HTML 구조 차이로 인해 정확한 확인이 어려울 수 있습니다)")
            else:
                logger.warning(f"로그인 상태 확인 중 예상치 못한 상태 코드: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"로그인 상태 확인 오류: {e}")
            # 로그인 상태 확인 실패해도 계속 진행 (쿠키가 올바르면 작동할 수 있음)
            logger.warning("로그인 상태 확인 실패했지만 계속 진행합니다. 오류가 발생하면 쿠키를 확인해주세요.")
        except Exception as e:
            logger.error(f"로그인 상태 확인 중 예외 발생: {e}")
            # 로그인 상태 확인 실패해도 계속 진행
            logger.warning("로그인 상태 확인 실패했지만 계속 진행합니다.")
    
    def _login(self):
        """티스토리에 로그인"""
        try:
            # 로그인 페이지 접근하여 CSRF 토큰 획득
            login_url = f"{self.BASE_URL}/auth/login"
            response = self.session.get(login_url)
            response.raise_for_status()
            
            # CSRF 토큰 추출
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = None
            
            # 다양한 방법으로 CSRF 토큰 찾기
            csrf_input = soup.find('input', {'name': '_csrf'})
            if not csrf_input:
                csrf_input = soup.find('input', {'name': 'csrf_token'})
            if not csrf_input:
                csrf_input = soup.find('input', {'name': 'csrf-token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            if not csrf_token:
                # 메타 태그에서 찾기
                csrf_meta = soup.find('meta', {'name': '_csrf'}) or \
                           soup.find('meta', {'name': 'csrf-token'}) or \
                           soup.find('meta', {'name': 'csrf_token'})
                if csrf_meta:
                    csrf_token = csrf_meta.get('content')
            
            if not csrf_token:
                # JavaScript 변수에서 찾기
                csrf_pattern = re.search(r'_csrf["\']?\s*[:=]\s*["\']([^"\']+)["\']', response.text)
                if csrf_pattern:
                    csrf_token = csrf_pattern.group(1)
            
            if not csrf_token:
                logger.warning("CSRF 토큰을 찾을 수 없습니다. 토큰 없이 시도합니다.")
                csrf_token = ""
            
            # 로그인 요청
            login_data = {
                'loginId': self.user_id,
                'password': self.user_pw
            }
            if csrf_token:
                login_data['_csrf'] = csrf_token
            
            login_response = self.session.post(
                login_url,
                data=login_data,
                allow_redirects=True
            )
            
            # 로그인 성공 확인
            if login_response.status_code == 200:
                # 로그인 성공 여부 확인
                if '로그아웃' in login_response.text or 'logout' in login_response.text.lower():
                    logger.info("티스토리 로그인 성공")
                elif '로그인' in login_response.text and 'loginId' in login_response.text:
                    raise Exception("로그인에 실패했습니다. 아이디와 비밀번호를 확인해주세요.")
                else:
                    # 쿠키 확인
                    if self.session.cookies:
                        logger.info("티스토리 로그인 성공 (쿠키 확인됨)")
                    else:
                        logger.warning("로그인 상태를 확인할 수 없습니다. 계속 진행합니다.")
            else:
                raise Exception(f"로그인 실패: HTTP {login_response.status_code}")
                
        except Exception as e:
            logger.error(f"로그인 오류: {e}")
            raise
    
    def _get_csrf_token(self) -> str:
        """글 작성 페이지에서 CSRF 토큰 획득"""
        try:
            # 글 작성 페이지 접근 (새로운 URL 패턴 사용)
            if self.blog_id:
                write_url = f"https://{self.blog_name}.tistory.com/manage/newpost/{self.blog_id}?type=post&returnURL=ENTRY"
            else:
                write_url = f"{self.BASE_URL}/manage/post/write"
            response = self.session.get(write_url, allow_redirects=True)
            
            # 로그인 페이지로 리다이렉트된 경우
            if '/login' in response.url or '/auth/login' in response.url:
                raise Exception("로그인이 필요합니다. 쿠키가 만료되었을 수 있습니다.")
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # CSRF 토큰 찾기
            csrf_input = soup.find('input', {'name': '_csrf'})
            if csrf_input:
                return csrf_input.get('value', '')
            
            # 메타 태그에서 찾기
            csrf_meta = soup.find('meta', {'name': '_csrf'})
            if csrf_meta:
                return csrf_meta.get('content', '')
            
            # JavaScript 변수에서 찾기
            csrf_pattern = re.search(r'_csrf["\']?\s*[:=]\s*["\']([^"\']+)["\']', response.text)
            if csrf_pattern:
                return csrf_pattern.group(1)
            
            raise Exception("CSRF 토큰을 찾을 수 없습니다.")
        except Exception as e:
            logger.error(f"CSRF 토큰 획득 오류: {e}")
            raise
    
    def get_category_list(self) -> List[Dict]:
        """카테고리 목록 조회"""
        try:
            # 먼저 글 작성 페이지 접근 시도 (새로운 URL 패턴 사용)
            if self.blog_id:
                write_url = f"https://{self.blog_name}.tistory.com/manage/newpost/{self.blog_id}?type=post&returnURL=ENTRY"
            else:
                write_url = f"{self.BASE_URL}/manage/post/write"
            response = self.session.get(write_url, allow_redirects=True)
            
            # 리다이렉트된 경우 최종 URL 확인
            final_url = response.url
            
            # 로그인 페이지로 리다이렉트된 경우
            if '/login' in final_url or '/auth/login' in final_url:
                logger.warning("로그인이 필요합니다. 쿠키가 만료되었을 수 있습니다.")
                return [{'id': '0', 'name': '미분류'}]
            
            if response.status_code != 200:
                logger.warning(f"글 작성 페이지 접근 실패: HTTP {response.status_code}")
                return [{'id': '0', 'name': '미분류'}]
            
            soup = BeautifulSoup(response.text, 'html.parser')
            categories = []
            
            # 카테고리 셀렉트 박스 찾기 (다양한 선택자 시도)
            category_select = None
            
            # 다양한 방법으로 select 태그 찾기
            selectors = [
                {'id': 'categoryId'},
                {'name': 'categoryId'},
                {'id': 'category'},
                {'name': 'category'},
                {'id': re.compile('category', re.I)},
                {'name': re.compile('category', re.I)},
                {'class': re.compile('category', re.I)},
            ]
            
            for selector in selectors:
                category_select = soup.find('select', selector)
                if category_select:
                    logger.debug(f"카테고리 select 태그를 찾았습니다: {selector}")
                    break
            
            # select 태그를 찾지 못한 경우, 모든 select 태그 검색
            if not category_select:
                all_selects = soup.find_all('select')
                logger.debug(f"찾은 select 태그 개수: {len(all_selects)}")
                for select in all_selects:
                    select_id = select.get('id', '')
                    select_name = select.get('name', '')
                    # 카테고리 관련 키워드가 포함된 select 찾기
                    if 'categor' in select_id.lower() or 'categor' in select_name.lower():
                        category_select = select
                        logger.debug(f"카테고리 select 태그 발견 (id: {select_id}, name: {select_name})")
                        break
            
            if category_select:
                for option in category_select.find_all('option'):
                    cat_id = option.get('value', '0')
                    cat_name = option.text.strip()
                    # 빈 값 제외
                    if cat_id and cat_id != '0' and cat_name:
                        categories.append({'id': cat_id, 'name': cat_name})
                        logger.debug(f"카테고리 찾음: {cat_id} - {cat_name}")
                
                # 미분류도 추가 (보통 value='0')
                categories.insert(0, {'id': '0', 'name': '미분류'})
            
            if categories:
                logger.info(f"{len(categories)}개의 카테고리를 찾았습니다.")
                # 찾은 카테고리 목록 로그 출력
                for cat in categories:
                    logger.info(f"  - {cat['name']} (ID: {cat['id']})")
                return categories
            else:
                logger.warning("카테고리를 찾을 수 없습니다. HTML 구조를 확인해주세요.")
                # 디버깅을 위해 HTML 일부 출력
                logger.debug(f"응답 URL: {final_url}")
                logger.debug(f"응답 길이: {len(response.text)} bytes")
                return [{'id': '0', 'name': '미분류'}]
            
        except Exception as e:
            logger.error(f"카테고리 조회 오류: {e}", exc_info=True)
            logger.info("카테고리 조회 실패 시 미분류(0)를 사용합니다.")
            return [{'id': '0', 'name': '미분류'}]
    
    def get_category_id_by_name(self, category_name: str) -> Optional[str]:
        """카테고리 이름으로 ID 조회"""
        categories = self.get_category_list()
        for category in categories:
            if category.get('name') == category_name:
                return category.get('id')
        return "0"  # 없으면 미분류
    
    def write_post(
        self,
        title: str,
        content: str,
        category_id: str = "0",
        visibility: int = 0,  # 0: 발행, 1: 비공개, 3: 보호
        tag: str = ""
    ) -> Dict:
        """
        글 작성
        
        Args:
            title: 제목
            content: 내용 (HTML)
            category_id: 카테고리 ID (0: 미분류)
            visibility: 공개 설정 (0: 공개, 1: 비공개, 3: 보호)
            tag: 태그 (쉼표로 구분)
        
        Returns:
            작성된 글 정보
        """
        try:
            # 글 작성 페이지 접근하여 필요한 토큰 및 정보 획득
            # 새로운 티스토리 글 작성 페이지 URL 패턴 사용
            if self.blog_id:
                # 브라우저 Referer와 동일한 형식 사용
                write_url = f"https://{self.blog_name}.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F"
            else:
                # blog_id가 없으면 기존 URL 패턴 시도
                write_urls = [
                    f"https://{self.blog_name}.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F",
                    f"{self.BASE_URL}/manage/post/write",
                    f"{self.BASE_URL}/manage/post",
                ]
                write_url = write_urls[0]
            
            response = self.session.get(write_url, allow_redirects=True)
                
            if response.status_code != 200:
                logger.error(f"글 작성 페이지 접근 실패: HTTP {response.status_code}, URL: {write_url}")
                logger.error(f"최종 리다이렉트 URL: {response.url}")
                raise Exception(f"글 작성 페이지 접근 실패: HTTP {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # CSRF 토큰 획득 (이미 가져온 응답에서 추출)
            csrf_token = None
            
            # input 태그에서 찾기
            csrf_input = soup.find('input', {'name': '_csrf'})
            if csrf_input:
                csrf_token = csrf_input.get('value', '')
            
            # 메타 태그에서 찾기
            if not csrf_token:
                csrf_meta = soup.find('meta', {'name': '_csrf'})
                if csrf_meta:
                    csrf_token = csrf_meta.get('content', '')
            
            # JavaScript 변수에서 찾기
            if not csrf_token:
                csrf_pattern = re.search(r'_csrf["\']?\s*[:=]\s*["\']([^"\']+)["\']', response.text)
                if csrf_pattern:
                    csrf_token = csrf_pattern.group(1)
            
            # TOP-XSRF-TOKEN 쿠키에서 가져오기 (이미 쿠키로 설정했을 수 있음)
            if not csrf_token:
                csrf_cookie = self.session.cookies.get('TOP-XSRF-TOKEN', domain='www.tistory.com')
                if csrf_cookie:
                    csrf_token = csrf_cookie
            
            if not csrf_token:
                logger.warning("CSRF 토큰을 찾을 수 없습니다. 토큰 없이 시도합니다.")
                csrf_token = ""
            
            # 글 작성 API 엔드포인트 (실제 티스토리 API 엔드포인트 사용)
            if self.blog_id:
                blog_base_url = f"https://{self.blog_name}.tistory.com"
                endpoints = [
                    # 실제 티스토리 글 작성 API 엔드포인트 (POST /manage/post.json)
                    f"{blog_base_url}/manage/post.json",
                    # 대체 엔드포인트들
                    f"{blog_base_url}/manage/post/save",
                    f"{blog_base_url}/manage/post/publish",
                    f"{blog_base_url}/manage/newpost/{self.blog_id}"
                ]
            else:
                blog_base_url = self.BASE_URL
                endpoints = [
                    # 실제 티스토리 글 작성 API 엔드포인트 (POST /manage/post.json)
                    f"{blog_base_url}/manage/post.json",
                    # 대체 엔드포인트들
                    f"{blog_base_url}/manage/post/save",
                    f"{blog_base_url}/manage/post/publish",
                    f"{blog_base_url}/manage/post/write"
                ]
            
            # 글 작성 시도 (일일 발행 제한 시 비공개로 재시도)
            success = False
            original_visibility = visibility
            tried_private = False  # 비공개 발행 재시도 여부
            
            # 재시도 루프: 일일 제한 시 비공개로 한 번 재시도
            max_attempts = 2
            last_response = None
            for attempt in range(max_attempts):
                if attempt > 0:
                    # 두 번째 시도: 비공개로 변경
                    if tried_private and original_visibility == 0:
                        logger.info(f"비공개 발행으로 재시도합니다 (시도 {attempt + 1}/{max_attempts})")
                        visibility = 1  # 비공개로 변경
                    else:
                        # 재시도할 이유가 없으면 종료
                        break
                
                # 글 작성 데이터 (JSON API용과 Form용 두 가지 형식 준비)
                blog_base_url = f"https://{self.blog_name}.tistory.com" if self.blog_id else self.BASE_URL
                
                # JSON API용 데이터 (post.json 엔드포인트 - 티스토리 실제 형식)
                json_data = {
                    'id': '0',  # 새 글 작성은 항상 0
                    'title': title,
                    'content': content,
                    'slogan': title,  # 슬로건은 제목과 동일하게
                    'category': int(category_id) if category_id.isdigit() else 0,
                    'tag': tag if tag else '',
                    'visibility': 20 if visibility == 0 else (10 if visibility == 1 else 30),  # 20: 공개, 10: 비공개, 30: 보호
                    'published': 1 if visibility == 0 else 0,  # 공개일 때만 발행
                    'type': 'post',
                    'uselessMarginForEntry': 1,
                    'attachments': [],
                    'cclCommercial': 0,
                    'cclDerive': 0,
                    'daumLike': '401',
                    'password': '',
                    'recaptchaValue': '',
                    'draftSequence': None
                }
                
                # Form 데이터 (기존 엔드포인트용)
                form_data = {
                    'blogName': self.blog_name,
                    'title': title,
                    'content': content,
                    'categoryId': category_id,
                    'tag': tag
                }
                
                if csrf_token:
                    form_data['_csrf'] = csrf_token
                    # JSON 요청에는 CSRF 토큰을 헤더에 포함하거나 요청에 포함할 수 있음
                    # 필요시 추가
                
                # 공개 설정 (Form용)
                if visibility == 0:  # 공개
                    form_data['visibility'] = '0'
                    form_data['publish'] = '1'
                elif visibility == 1:  # 비공개
                    form_data['visibility'] = '1'
                    form_data['publish'] = '0'
                else:  # 보호
                    form_data['visibility'] = '3'
                    form_data['publish'] = '0'
                
                # 헤더 설정 (브라우저와 동일하게)
                headers_json = {
                    'Accept': 'application/json, text/plain, */*',
                    'Content-Type': 'application/json',
                    'Origin': blog_base_url,
                    'Referer': write_url,
                    'Sec-Fetch-Dest': 'empty',
                    'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Site': 'same-origin',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
                }
                
                # CSRF 토큰은 쿠키에 이미 포함되어 있으므로 헤더에 별도로 추가하지 않음
                
                headers_form = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': write_url,
                    'Origin': blog_base_url
                }
            
                for endpoint in endpoints:
                    try:
                        response = None
                        
                        # JSON API 엔드포인트인 경우
                        if endpoint.endswith('.json'):
                            logger.info(f"POST 요청 시도 (JSON API): {endpoint}")
                            response = self.session.post(
                                endpoint,
                                json=json_data,
                                headers=headers_json,
                                allow_redirects=True
                            )
                        
                            # 200 응답이면 성공
                            if response.status_code == 200:
                                try:
                                    result = response.json()
                                    logger.info(f"JSON API 응답 내용: {result}")
                                    
                                    # 응답에서 URL 또는 ID 추출
                                    post_url = result.get('entryUrl') or result.get('permalink') or result.get('url', '')
                                    post_id = result.get('id', '')
                                    
                                    if post_url or post_id:
                                        logger.info(f"포스트 작성 성공 (JSON API): {title}, URL: {post_url}")
                                        return {
                                            'status': 'success',
                                            'title': title,
                                            'id': post_id,
                                            'url': post_url
                                        }
                                    else:
                                        # URL/ID가 없어도 200이면 성공
                                        logger.info(f"포스트 작성 성공 (JSON API, 200 OK): {title}")
                                        return {'status': 'success', 'title': title}
                                except Exception as e:
                                    logger.warning(f"JSON 파싱 실패: {e}, 응답: {response.text[:200]}")
                                    # 200이면 성공으로 간주
                                    logger.info(f"포스트 작성 성공 (200 OK): {title}")
                                    return {'status': 'success', 'title': title}
                            elif response.status_code == 403:
                                # 일일 발행 제한 등의 403 오류 처리
                                error_text = response.text[:200] if response.text else ""
                                logger.warning(f"JSON API 403 오류: {error_text}")
                                if ("15개" in error_text or "발행" in error_text) and original_visibility == 0:
                                    # 일일 발행 제한에 도달했고 원래 공개였으면 비공개로 재시도
                                    logger.warning("일일 발행 제한에 도달했습니다. 비공개로 발행을 시도합니다.")
                                    tried_private = True
                                continue
                            else:
                                logger.warning(f"JSON API 응답 상태 코드: {response.status_code}, 응답 내용: {response.text[:200]}")
                                continue
                        else:
                            # Form 엔드포인트인 경우
                            logger.info(f"POST 요청 시도 (Form API): {endpoint}")
                            response = self.session.post(
                                endpoint,
                                data=form_data,
                                headers=headers_form,
                                allow_redirects=True
                            )
                        
                            if not response:
                                logger.warning(f"응답이 없습니다: {endpoint}")
                                continue
                            
                            # Form 엔드포인트 응답 처리
                            if response.status_code in [200, 201, 302]:
                                
                                # 리다이렉트 응답 처리
                                if response.status_code == 302:
                                    location = response.headers.get('Location', '')
                                    if '/manage/post/list' in location or '/manage/post/view' in location or '/manage/posts' in location:
                                        success = True
                                        logger.info(f"포스트 작성 성공 (리다이렉트): {title}")
                                        return {'status': 'success', 'title': title, 'url': location}
                                
                                # 일반 응답 처리
                                if response.status_code in [200, 201]:
                                    # 응답 텍스트 확인
                                    response_text = response.text.lower()
                                    if 'success' in response_text or '작성되었습니다' in response_text or '/manage/post/list' in response.url or '/manage/posts' in response.url:
                                        success = True
                                        logger.info(f"포스트 작성 성공: {title}")
                                        return {'status': 'success', 'title': title}
                    except Exception as e:
                        logger.debug(f"엔드포인트 {endpoint} 시도 실패: {e}")
                        continue
                    
                    # 응답 저장 (에러 메시지용)
                    if response:
                        last_response = response
                    
                    # 성공했으면 외부 루프도 종료
                    if success:
                        break
                
                # 성공했으면 재시도 루프 종료
                if success:
                    break
                
                # 실패했는데 비공개로 재시도해야 하면 다음 시도로
                if not success and tried_private and attempt < max_attempts - 1:
                    continue
            
            if not success:
                # 마지막 응답 정보 포함
                last_status = last_response.status_code if last_response else "N/A"
                last_response_text = last_response.text[:500] if last_response and last_response.text else "N/A"
                raise Exception(f"글 작성 실패: 모든 엔드포인트 시도 실패 (마지막 상태 코드: {last_status}, 응답: {last_response_text})")
            
        except Exception as e:
            logger.error(f"글 작성 오류: {e}")
            raise
