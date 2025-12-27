# 🍪 티스토리 쿠키 추출 가이드

티스토리는 카카오 계정으로 로그인할 수 있습니다. 브라우저에서 카카오로 로그인한 후 쿠키를 추출하여 사용합니다.

## 목차

1. [Chrome/Edge에서 쿠키 추출](#1-chromeedge에서-쿠키-추출)
2. [쿠키 추출 스크립트 (자동)](#2-쿠키-추출-스크립트-자동)
3. [쿠키 형식 예시](#3-쿠키-형식-예시)
4. [설정 파일에 적용](#설정-파일에-적용)
5. [쿠키 만료 및 갱신](#쿠키-만료-및-갱신)
6. [보안 주의사항](#보안-주의사항)
7. [팁](#팁)
8. [문제 해결](#쿠키를-찾을-수-없는-경우)

## 📋 카카오 로그인 쿠키 추출 방법

### 1. **Chrome/Edge에서 쿠키 추출**

1. **티스토리에 카카오 로그인**
   - https://www.tistory.com 접속
   - 카카오 로그인 선택하여 로그인

2. **개발자 도구 열기**
   - `F12` 또는 `Cmd+Option+I` (Mac) / `Ctrl+Shift+I` (Windows)
   - **Application** 탭 클릭 (Chrome) 또는 **Storage** 탭 (Firefox)

3. **쿠키 확인**
   - 왼쪽 메뉴: **Storage** → **Cookies** → `https://www.tistory.com` **⚠️ 중요: www.tistory.com 도메인 확인**
   - `.tiara.tistory.com`이나 다른 도메인이 아닌 `www.tistory.com`의 쿠키를 확인해야 합니다
   - 중요한 인증 쿠키 찾기:
     - `TSSESSION` (티스토리 세션 쿠키) - 가장 중요! ⭐
     - `_T_ANO` (티스토리 인증 토큰) - 가장 중요! ⭐
     - `TOP-XSRF-TOKEN` (CSRF 토큰, www.tistory.com 도메인) - 중요! ⭐
     - `JSESSIONID` (Java 세션 ID, 구형)
     - `TISTORY` (티스토리 인증 토큰, 구형)
     - `kakao` 관련 쿠키 (있는 경우)
     - 기타 인증 관련 쿠키
   - ⚠️ `TSID`, `TUID`, `UUID`, `_ga`, `FCCDCF`, `FCNEC` 등은 추적/분석용 쿠키로 인증에 사용되지 않습니다

4. **쿠키 복사**
   - 각 쿠키의 **Name**과 **Value**를 복사
   - 형식: `name1=value1; name2=value2; ...`

### 2. **쿠키 추출 스크립트 (자동)**

**Console 탭**에서 다음 스크립트 실행:

```javascript
// 모든 쿠키를 문자열로 출력
console.log(document.cookie);
```

또는 JSON 형태로:

```javascript
// 모든 쿠키를 JSON 형태로 출력
const cookies = {};
document.cookie.split(';').forEach(cookie => {
    const [name, value] = cookie.trim().split('=');
    cookies[name] = value;
});
console.log(JSON.stringify(cookies, null, 2));
```

### 3. **쿠키 형식 예시**

**올바른 쿠키 예시 (인증용):**

최신 방식 (권장):
```
TSSESSION=b9b65f634b9d6fbc6682aa7509e755f58ade1041; _T_ANO=dYxje7Dn7qBL1cLFHtPkrcNfh0MJlqSx1wJJuTrIRtQCH5TcA3h4o36peAvkTasxiVnCYOsez7YvGPn+M2k0M13POkEL7xilcabP66SQUtJzdUaQ/p/6eqIikk7/5BavK6iJfA60N/1n8sCYQ7GVdEquuTol7sbmtvO4DsZKkDHPjXGENWi0rNF3YJmKcjypgsNU8wEuI3FpuvlOrWXlDQJvinqPmtEzbDxDoO0uJzl5Ke0/U/TVEUEdeU+tvlfaE/OICT5nMgQP7IFx/q8N+kpabAIjj4/kvI95/wgmXufhymjyxBovjAkNyqdk7oenlceOn5nGP2nM3/s7SNG7Ng==; TOP-XSRF-TOKEN=5202139c-0227-4979-8390-c369138e7bed
```

구형 방식:
```
JSESSIONID=w-akFaskTPeNMK_251227220947733; TISTORY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**⚠️ 주의:**
- `TSID`, `TUID`, `UUID`, `_ga`, `FCCDCF`, `FCNEC` 등은 추적/분석용 쿠키로 인증에 사용되지 않습니다
- `TSSESSION`과 `_T_ANO`가 가장 중요한 인증 쿠키입니다
- `TOP-XSRF-TOKEN`은 `www.tistory.com` 도메인에 있습니다
- `.tiara.tistory.com` 도메인의 쿠키는 사용하지 마세요

**쿠키를 찾을 수 없는 경우:**
1. `www.tistory.com` 도메인에서 로그인 상태를 확인하세요
2. 관리자 페이지(`https://www.tistory.com/manage/post`)로 이동한 후 쿠키를 확인하세요
3. 로그인 후 잠시 기다린 후 쿠키를 확인하세요

## 🔧 설정 파일에 적용

### `config.yaml` 파일 편집

```yaml
tistory:
  cookies: "JSESSIONID=ABC123XYZ; TISTORY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  blog_name: "your_blog_name"
```

**주의사항:**
- 쿠키는 민감한 정보이므로 `.gitignore`에 포함되어 있습니다
- 쿠키는 만료될 수 있으므로, 만료되면 다시 추출해야 합니다
- 쿠키 값에 공백이나 특수문자가 포함될 수 있으므로 따옴표로 감싸세요

## ⏰ 쿠키 만료 및 갱신

- 쿠키는 보통 몇 시간에서 며칠 동안 유효합니다
- 만료되면 다시 브라우저에서 로그인하여 새 쿠키를 추출하세요
- 프로그램 실행 시 로그인 오류가 발생하면 쿠키 만료를 확인하세요

## 🔒 보안 주의사항

- `config.yaml` 파일은 절대 Git에 커밋하지 마세요
- `.gitignore`에 `config.yaml`이 포함되어 있는지 확인하세요
- 쿠키 정보는 다른 사람과 공유하지 마세요

## 💡 팁

- 쿠키를 추출할 때는 **로그인 직후**에 추출하는 것이 좋습니다
- 여러 쿠키 중에서 가장 중요한 것은 `TSSESSION`과 `_T_ANO`입니다 (최신 방식)
- `TOP-XSRF-TOKEN`도 포함하는 것을 권장합니다
- 일부 쿠키가 없어도 작동할 수 있으므로, 우선 필수 쿠키만 포함해보세요
- **반드시 `www.tistory.com` 도메인의 쿠키만 사용**하세요
- `.tiara.tistory.com` 도메인의 쿠키는 사용하지 마세요 (추적용일 뿐)

## ❓ 쿠키를 찾을 수 없는 경우

1. **올바른 도메인 확인**: `www.tistory.com` 도메인의 쿠키를 확인하세요
2. **로그인 상태 확인**: 관리자 페이지(`https://www.tistory.com/manage/post`)에 접속할 수 있는지 확인하세요
3. **쿠키 이름 확인**: 
   - 최신 방식: `TSSESSION`, `_T_ANO`, `TOP-XSRF-TOKEN` 확인
   - 구형 방식: `JSESSIONID`, `TISTORY` 확인
   - 세션 관련: `TSSESSION`, `session`, `sid`, `sessionid` 등
   - 인증 관련: `_T_ANO`, `auth`, `token`, `access_token` 등
4. **새로고침**: 페이지를 새로고침한 후 쿠키를 다시 확인하세요

