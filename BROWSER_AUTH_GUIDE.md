# 브라우저 자동화를 통한 쿠키 갱신 가이드

## 개요

브라우저 자동화(Selenium)를 사용하여 카카오 로그인을 통해 티스토리 쿠키를 자동으로 갱신하는 기능입니다.

## 설정 방법

### 1. config.yaml 설정

`config.yaml`에 다음 설정을 추가하세요:

```yaml
tistory:
  cookies: "TSSESSION=xxx; _T_ANO=yyy; ..."  # 기존 쿠키
  blog_name: "your_blog_name"
  blog_id: "99"

# 브라우저 자동화를 통한 쿠키 갱신 설정
browser_auth:
  kakao_email: "your_kakao_email@example.com"  # 카카오 계정 이메일
  kakao_password: "your_kakao_password"         # 카카오 계정 비밀번호
  headless: true                                 # true: 브라우저 창 안 띄움, false: 브라우저 창 띄움 (수동 인증 필요 시)
  auto_refresh: true                             # 자동 쿠키 갱신 활성화 (7일마다)
```

### 2. Chrome/ChromeDriver 설치

#### 로컬 환경 (macOS/Windows)

1. Chrome 브라우저 설치 (이미 설치되어 있을 수 있음)
2. Python 패키지 설치:
   ```bash
   pip install selenium webdriver-manager
   ```
3. `webdriver-manager`가 자동으로 ChromeDriver를 설치합니다.

#### Docker 환경

Dockerfile에 Chrome이 포함되어 있으므로 추가 설치가 필요 없습니다.

## 사용 방법

### 방법 1: 자동 갱신 (권장)

`config.yaml`에서 `browser_auth.auto_refresh: true`로 설정하면, 프로그램 시작 시 쿠키가 7일 이상 오래되었을 경우 자동으로 갱신합니다.

```yaml
browser_auth:
  auto_refresh: true  # 자동 갱신 활성화
```

### 방법 2: 수동 갱신

쿠키를 수동으로 갱신하려면:

```bash
# 로컬 환경
python scripts/refresh_cookies.py

# Docker 환경
docker compose run --rm tistory-writer python scripts/refresh_cookies.py
```

이 스크립트는:
1. 카카오 계정으로 티스토리 로그인
2. 쿠키 추출
3. `config.yaml`에 자동 업데이트

### 방법 3: 수동 인증이 필요한 경우

2단계 인증이나 추가 보안 검증이 필요한 경우:

1. `config.yaml`에서 `headless: false` 설정:
   ```yaml
   browser_auth:
     headless: false  # 브라우저 창을 띄워서 수동 인증 가능
   ```

2. `refresh_cookies.py` 실행:
   ```bash
   python scripts/refresh_cookies.py
   ```

3. 브라우저 창에서 수동으로 인증 완료
4. 스크립트가 자동으로 쿠키 추출 및 저장

## 주의사항

### 보안

- **카카오 계정 비밀번호를 config.yaml에 저장하는 것은 보안상 위험할 수 있습니다.**
- 가능하면 환경 변수나 비밀 관리 시스템을 사용하는 것을 권장합니다.
- `config.yaml`은 `.gitignore`에 포함되어 있는지 확인하세요.

### 카카오 보안 정책

카카오는 다음과 같은 보안 정책을 사용할 수 있습니다:
- 2단계 인증 (2FA)
- 모바일 인증 (SMS/앱 인증)
- 자동화 봇 감지

이러한 경우 `headless: false`로 설정하고 수동 인증을 완료해야 합니다.

### Docker 환경

Docker 컨테이너에서 브라우저 자동화를 사용하려면:
- Chrome 브라우저가 Dockerfile에 포함되어 있어야 합니다 (이미 포함됨)
- 헤드리스 모드가 기본값입니다 (`headless: true`)
- GUI가 필요한 경우 (`headless: false`) Xvfb 같은 가상 디스플레이가 필요할 수 있습니다

### 쿠키 유효 기간

- 쿠키는 약 30일 정도 유효합니다
- 자동 갱신은 7일 이상 경과된 경우에만 실행됩니다
- 더 자주 갱신하려면 `refresh_cookies.py`를 수동으로 실행하세요

## 트러블슈팅

### "Selenium이 설치되지 않았습니다" 오류

```bash
pip install selenium webdriver-manager
```

### "ChromeDriver를 찾을 수 없습니다" 오류

`webdriver-manager`가 자동으로 설치합니다. 수동 설치가 필요한 경우:
1. [ChromeDriver 다운로드](https://chromedriver.chromium.org/)
2. PATH에 추가하거나 Python에서 직접 경로 지정

### "카카오 로그인 버튼을 찾을 수 없습니다" 오류

티스토리 웹사이트 구조가 변경되었을 수 있습니다. `browser_auth.py`의 선택자를 업데이트해야 할 수 있습니다.

### "2단계 인증이 필요합니다" 오류

`headless: false`로 설정하고 수동으로 인증을 완료하세요.

### Docker에서 브라우저 실행 실패

Dockerfile에 Chrome이 제대로 설치되었는지 확인하세요. 필요시 로그를 확인:
```bash
docker compose logs tistory-writer
```

## 로그 확인

쿠키 갱신 과정은 로그에 기록됩니다:

```bash
# 로컬 환경
tail -f data/tistory_poster.log

# Docker 환경
docker compose logs -f tistory-writer
```

## API 참조

### BrowserAuth 클래스

```python
from src.auth.browser_auth import BrowserAuth

# 브라우저 인증 객체 생성
with BrowserAuth(headless=True) as auth:
    # 카카오 로그인
    cookies = auth.login_with_kakao("email@example.com", "password")
    print(cookies)  # 쿠키 문자열 출력
```

### CookieRefresher 클래스

```python
from src.utils.cookie_refresher import CookieRefresher

# 쿠키 갱신 관리자
refresher = CookieRefresher("config.yaml")

# 필요시 쿠키 갱신 (7일 이상 경과된 경우)
if refresher.refresh_cookies_if_needed():
    print("쿠키 갱신 완료!")

# 강제 갱신
refresher.refresh_cookies_if_needed(force=True)
```

