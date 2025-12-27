# Tistory 자동 포스팅 프로그램

티스토리 블로그에 매일 자동으로 AI 논문 리뷰 포스트를 작성하는 프로그램입니다.

## 주요 기능

- ✅ **OpenAI API 활용**: 중요도 및 인용수 기준으로 논문 리스트 자동 생성
- ✅ **AI 논문 리뷰 생성**: OpenAI GPT로 상세한 논문 리뷰 자동 생성
- ✅ **매일 자동 포스팅**: 오후 6시~11:59 사이 랜덤 시간에 자동 포스팅
- ✅ **순차적 리뷰**: 논문 리스트에서 순서대로 하나씩 리뷰
- ✅ **지정 카테고리**: PaperReview 카테고리에 자동 분류
- ✅ **Docker & uv**: 컨테이너화 및 빠른 의존성 관리
- ✅ **리눅스 실행**: restart: always로 계속 실행

## 빠른 시작 (Docker 사용)

### 1. 설정 파일 생성

```bash
cp config.yaml.example config.yaml
```

### 2. 설정 파일 편집

`config.yaml` 파일을 열어 티스토리 및 OpenAI API 정보를 입력하세요:

```yaml
tistory:
  # 카카오 로그인 사용 시: 쿠키 방식 사용 (권장)
  cookies: "TSSESSION=xxx; _T_ANO=yyy; TOP-XSRF-TOKEN=zzz; ..."
  blog_name: "your_blog_name"        # 블로그 이름 (예: example.tistory.com의 example)
  blog_id: "99"                      # 블로그 ID (선택적, 글쓰기 페이지 URL에서 확인)

category:
  name: "PaperReview"                # 카테고리 이름
  id: "1329459"                      # 카테고리 ID (선택적, 티스토리 API 응답에서 확인 가능)

openai:
  api_key: "YOUR_OPENAI_API_KEY"     # OpenAI API 키
  model: "gpt-4o-mini"               # 사용할 모델 (gpt-4o-mini, gpt-4o, gpt-5.2 등)

prompts_file: "prompts.yaml"         # 프롬프트 설정 파일 경로

paper_collection:
  topic: "AI/ML"                     # 논문 주제
  count: 100                         # 논문 개수
  recent_years: 5                     # 최근 몇 년간의 논문만 선택

schedule:
  start_hour: 18                     # 오후 6시
  end_hour: 23                       # 오후 11시
  end_minute: 59                     # 59분
```

**중요 설정:**
- `blog_id`: 글쓰기 페이지 URL에서 확인 (예: `https://your-blog.tistory.com/manage/newpost/99` → `99`)
- `category.id`: 티스토리 API 응답에서 확인하거나, 카테고리 이름으로 자동 조회
- `cookies`: 카카오 로그인 시 필수 (자세한 방법은 `COOKIE_GUIDE.md` 참고)

### 3. 프롬프트 설정 (선택적)

프롬프트를 커스터마이징하려면:

```bash
# 프롬프트 파일 생성
cp prompts.yaml.example prompts.yaml
```

`prompts.yaml` 파일을 편집하여 프롬프트를 수정할 수 있습니다. `{}`로 감싼 변수를 사용할 수 있습니다:

**논문 리스트 생성 프롬프트 변수:**
- `{topic}`: 논문 주제
- `{count}`: 논문 개수
- `{recent_years}`: 최근 몇 년간

**논문 리뷰 생성 프롬프트 변수:**
- `{title}`: 논문 제목
- `{authors}`: 저자 목록
- `{year}`: 발행년도
- `{citations}`: 인용수
- `{arxiv_id}`: arXiv ID
- `{url}`: 논문 URL
- `{abstract}`: 논문 초록

자세한 프롬프트 구조는 `prompts.yaml.example` 파일을 참고하세요.

### 4. 논문 리스트 생성

#### 방법 1: OpenAI로 자동 생성 (최초 1회)

```bash
# 논문 리스트 수집
python collect_papers.py
```

이 스크립트는:
- OpenAI API로 중요도 및 인용수 기준 논문 리스트 생성
- `data/papers.json`에 저장
- 중요도 순으로 자동 정렬

#### 방법 2: 수동으로 논문 추가

```bash
# 템플릿 파일 생성
cp papers_template.json my_papers.json

# my_papers.json 파일을 편집하여 논문 정보 입력
# 그 다음 추가:
python add_papers.py my_papers.json
```

논문 파일 형식:
```json
{
  "papers": [
    {
      "title": "논문 제목",
      "authors": ["저자1", "저자2"],
      "year": 2024,
      "citations": 1000,
      "arxiv_id": "2401.00001",
      "url": "https://arxiv.org/abs/2401.00001",
      "abstract": "논문 초록",
      "importance_score": 90
    }
  ]
}
```

### 5. 데이터 디렉토리 생성 (선택적)

```bash
# 데이터 디렉토리 생성 (자동 생성되지만 미리 만들어도 됨)
mkdir -p data
```

### 6. Docker Compose로 실행

```bash
# 빌드 및 실행
docker compose up -d

# 로그 확인
docker compose logs -f

# 중지
docker compose down

# 재빌드 후 실행
docker compose up -d --build
```

### 7. 상태 확인

```bash
# 실행 중인 컨테이너 확인
docker compose ps

# 로그 실시간 확인
docker compose logs -f tistory-writer

# 컨테이너 내부 접속
docker compose exec tistory-writer bash

# 컨테이너 내부에서 직접 실행 (디버깅용)
docker compose run --rm tistory-writer python test_post.py
```

## 티스토리 인증 설정

### 방법 1: 쿠키 사용 (카카오 로그인 권장) ⭐

티스토리는 카카오 계정으로 로그인할 수 있습니다. 브라우저에서 카카오로 로그인한 후 쿠키를 추출하여 사용합니다.

**빠른 가이드:**
1. 티스토리에 **카카오 로그인**으로 로그인
2. 브라우저 개발자 도구 열기 (F12)
3. **Application** 탭 > **Cookies** > `https://www.tistory.com`
4. 중요한 쿠키 복사:
   - `TSSESSION` (필수)
   - `_T_ANO` (필수)
   - `TOP-XSRF-TOKEN` (권장)
5. `config.yaml`의 `cookies` 필드에 붙여넣기

**자세한 방법**: `COOKIE_GUIDE.md` 파일 참고

```yaml
tistory:
  cookies: "TSSESSION=xxx; _T_ANO=yyy; TOP-XSRF-TOKEN=zzz; ..."
  blog_name: "your_blog_name"
  blog_id: "99"  # 글쓰기 페이지 URL에서 확인
```

### 방법 2: ID/비밀번호 사용 (비권장)

```yaml
tistory:
  user_id: "your_id"
  user_pw: "your_password"
  blog_name: "your_blog_name"
  blog_id: "99"
```

**주의**: 
- 티스토리는 카카오 계정 연동을 권장합니다
- ID/비밀번호 방식은 보안 정책 변경으로 작동하지 않을 수 있습니다
- **카카오 로그인을 사용하는 경우 쿠키 방식을 강력히 권장합니다**

### 블로그 설정 확인

- **블로그 이름**: 블로그 URL이 `https://example.tistory.com`이면 `example`
- **블로그 ID**: 글쓰기 페이지 URL에서 확인
  - 예: `https://example.tistory.com/manage/newpost/99` → `blog_id: "99"`
- **카테고리 ID**: 티스토리 API 응답에서 확인하거나, 카테고리 이름으로 자동 조회
  - 설정 파일에 직접 지정 가능: `category.id: "1329459"`

## 로컬 개발 (Docker 없이)

### 설치

```bash
# uv 설치 (권장)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 의존성 설치
uv pip install -e .

# 또는 pip 사용
pip install -r requirements.txt
```

### 실행

```bash
# 테스트 포스팅 (즉시 실행)
python test_post.py

# 자동 포스팅 시작
python main.py
```

## 파일 구조

```
Tistory_writer/
├── main.py                 # 메인 스크립트
├── tistory_api.py          # 티스토리 웹 인터페이스 클라이언트
├── openai_client.py        # OpenAI API 클라이언트
├── paper_manager.py        # 논문 리스트 관리
├── paper_collector.py      # 논문 리스트 수집기
├── content_generator.py    # 논문 리뷰 콘텐츠 생성기
├── post_manager.py         # 포스트 번호 관리
├── scheduler.py            # 스케줄러
├── collect_papers.py       # 논문 리스트 수집 스크립트
├── add_papers.py           # 논문 수동 추가 스크립트
├── test_post.py            # 테스트 스크립트
├── config.yaml             # 설정 파일 (직접 생성)
├── config.yaml.example     # 설정 파일 예시
├── prompts.yaml            # 프롬프트 설정 파일 (직접 생성)
├── prompts.yaml.example    # 프롬프트 설정 파일 예시
├── papers_template.json    # 논문 템플릿 파일
├── pyproject.toml          # uv 프로젝트 설정
├── requirements.txt        # pip 의존성 (호환성용)
├── Dockerfile              # Docker 이미지 빌드
├── docker-compose.yml      # Docker Compose 설정
├── .dockerignore           # Docker 빌드 제외 파일
├── data/                   # 데이터 디렉토리
│   ├── papers.json         # 논문 리스트 (자동 생성)
│   ├── paper_state.json    # 논문 진행 상태 (자동 생성)
│   ├── post_state.json     # 포스트 번호 상태 (자동 생성)
│   └── tistory_poster.log  # 로그 파일
└── README.md               # 이 파일
```

## Docker 볼륨

다음 파일/디렉토리들은 호스트와 마운트되어 컨테이너를 재시작해도 상태가 유지됩니다:

- `config.yaml` - 설정 파일 (읽기 전용)
- `data/` - 데이터 디렉토리
  - `post_state.json` - 포스트 번호 상태 (자동 생성)
  - `tistory_poster.log` - 로그 파일 (자동 생성)

## 리눅스 서버 배포

### systemd 서비스로 등록 (선택적)

```ini
# /etc/systemd/system/tistory-writer.service
[Unit]
Description=Tistory Auto Poster
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/Tistory_writer
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=always

[Install]
WantedBy=multi-user.target
```

서비스 활성화:

```bash
sudo systemctl enable tistory-writer.service
sudo systemctl start tistory-writer.service
```

### 직접 실행

```bash
# 백그라운드 실행
docker compose up -d

# 자동 재시작 설정 확인
docker compose ps
```

## 리눅스 서버 배포

리눅스 서버에서 스케줄러 모드로 실행하는 방법은 다음 문서를 참고하세요:

- **[DEPLOY.md](DEPLOY.md)**: 기본 배포 가이드
- **[DEPLOY_GITHUB.md](DEPLOY_GITHUB.md)**: GitHub을 통한 배포 가이드 (권장)

**빠른 시작:**

```bash
# 1. GitHub에서 클론
git clone <your-repo-url>
cd Tistory_writer

# 2. 설정 파일 생성
cp config.yaml.example config.yaml
nano config.yaml  # 스케줄러 활성화: schedule.enabled: true

# 3. 실행
docker compose up -d --build

# 4. 로그 확인
docker compose logs -f
```

## 문제 해결

### 카테고리를 찾을 수 없습니다

- `config.yaml`의 `category.name`이 티스토리 블로그의 카테고리 이름과 정확히 일치하는지 확인
- 카테고리 ID를 직접 지정: `category.id: "1329459"` (티스토리 API 응답에서 확인)
- 카테고리 조회 테스트: `python test_category.py`
- 카테고리가 없으면 미분류(0)로 게시됩니다

### 쿠키가 만료되었습니다

- 쿠키는 보통 몇 시간에서 며칠 동안 유효합니다
- 브라우저에서 다시 로그인하여 새 쿠키를 추출하세요
- `COOKIE_GUIDE.md` 파일 참고
- 컨테이너 재시작:
  ```bash
  docker compose restart
  ```

### 컨테이너가 계속 재시작됩니다

- 로그 확인: `docker compose logs tistory-writer`
- 설정 파일 오류가 있는지 확인: `config.yaml` 문법 검사
- 컨테이너 내부에서 직접 실행하여 오류 확인:
  ```bash
  docker compose run --rm tistory-writer python test_post.py
  ```

### 시간대가 맞지 않습니다

- `docker-compose.yml`의 `TZ=Asia/Seoul` 환경 변수를 확인
- 컨테이너 시간대 확인:
  ```bash
  docker compose exec tistory-writer date
  ```

### 글 작성이 실패합니다 (405 오류)

- 티스토리 글 작성 API 엔드포인트가 변경되었을 수 있습니다
- 브라우저 개발자 도구에서 실제 POST 요청 URL 확인 필요
- `blog_id` 설정이 올바른지 확인

### OpenAI API 오류

- `gpt-5.2` 같은 새 모델은 `max_completion_tokens`를 사용합니다 (자동 처리됨)
- API 키가 유효한지 확인
- 모델 이름이 올바른지 확인 (예: `gpt-4o-mini`, `gpt-4o`)

## 상태 관리

프로그램은 `post_state.json` 파일에 마지막 포스트 번호를 저장합니다. 이 파일이 없으면 자동으로 생성되며, 1번부터 시작합니다.

## 로그

로그는 `tistory_poster.log` 파일과 Docker 로그에 저장됩니다:

```bash
# 파일 로그
tail -f tistory_poster.log

# Docker 로그
docker compose logs -f tistory-writer
```

## 테스트

### 즉시 포스팅 테스트

```bash
# Docker 컨테이너에서
docker compose exec tistory-writer python test_post.py

# 로컬에서
python test_post.py
```

### 카테고리 조회 테스트

```bash
# Docker 컨테이너에서
docker compose exec tistory-writer python test_category.py

# 로컬에서
python test_category.py
```

## 주요 기능 상세

### 1. 논문 리스트 관리
- OpenAI API로 중요도 및 인용수 기준 논문 리스트 자동 생성
- 수동으로 논문 추가 가능 (`add_papers.py`)
- 논문 리스트는 중요도 순으로 자동 정렬
- 리뷰 완료된 논문은 자동으로 스킵

### 2. AI 논문 리뷰 생성
- OpenAI GPT를 사용한 상세한 논문 리뷰 자동 생성
- 프롬프트 커스터마이징 가능 (`prompts.yaml`)
- 문제 정의 중심의 리뷰 구조 (학습 목적)
- 마크다운 형식으로 작성 후 HTML로 변환

### 3. 자동 포스팅
- 매일 오후 6시~11:59 사이 랜덤 시간에 자동 포스팅
- 지정된 카테고리에 자동 분류
- 순차적 포스트 번호 관리
- 실패 시 자동 재시도

### 4. 상태 관리
- 포스트 번호 상태 저장 (`post_state.json`)
- 논문 진행 상태 저장 (`paper_state.json`)
- 컨테이너 재시작 후에도 상태 유지

## 기술 스택

- **Python 3.11**: 메인 프로그래밍 언어
- **OpenAI API**: 논문 리스트 및 리뷰 생성
- **Requests**: HTTP 요청 (티스토리 웹 인터페이스)
- **BeautifulSoup4**: HTML 파싱 (CSRF 토큰, 카테고리 추출)
- **APScheduler**: 스케줄링 (랜덤 시간 포스팅)
- **Docker & Docker Compose**: 컨테이너화 및 배포
- **uv**: 빠른 Python 패키지 관리

## 라이선스

개인 사용 목적으로 제작되었습니다.
