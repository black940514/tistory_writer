# GitHub 배포 가이드

GitHub에 코드를 업로드하고 리눅스 서버에서 배포하는 전체 과정입니다.

## 1. GitHub에 코드 업로드

### 1.1 로컬에서 Git 초기화 (처음인 경우)

```bash
cd /Users/kimtaeyoun/Personal/Dev/Tistory_writer

# Git 초기화
git init

# .gitignore 확인 (config.yaml, data/ 등이 제외되는지 확인)
cat .gitignore
```

### 1.2 GitHub 저장소 생성

1. GitHub에서 새 저장소 생성 (예: `tistory-auto-poster`)
2. 저장소 URL 복사 (예: `https://github.com/yourusername/tistory-auto-poster.git`)

### 1.3 코드 커밋 및 푸시

```bash
# 원격 저장소 추가
git remote add origin <your-github-repo-url>

# 모든 파일 추가
git add .

# 커밋
git commit -m "Initial commit: Tistory auto poster"

# GitHub에 푸시
git push -u origin main
```

**중요**: `.gitignore`에 의해 다음 파일/디렉토리는 업로드되지 않습니다:
- `config.yaml` (민감한 정보 포함)
- `prompts.yaml` (커스텀 프롬프트)
- `data/` (논문 리스트, 상태 파일 등)
- `*.log` (로그 파일)

이들은 리눅스 서버에서 직접 생성해야 합니다.

## 2. 리눅스 서버에서 배포

### 2.1 필수 요구사항

- Docker 설치
- Docker Compose 설치
- Git 설치

### 2.2 서버에서 프로젝트 클론

```bash
# 작업 디렉토리로 이동 (예: /opt)
cd /opt

# GitHub에서 클론
git clone <your-github-repo-url> Tistory_writer
cd Tistory_writer
```

### 2.3 설정 파일 생성 및 data 디렉토리 생성

```bash
# 설정 파일 복사
cp config.yaml.example config.yaml

# data 디렉토리 생성 (필수 - 볼륨 마운트를 위해 필요)
mkdir -p data

# 설정 파일 편집
nano config.yaml
```

**필수 설정 항목:**

1. **Tistory 인증** (쿠키 방식 권장):
   ```yaml
   tistory:
     cookies: "TSSESSION=...; _T_ANO=...; TOP-XSRF-TOKEN=..."
     blog_name: "your-blog-name"
     blog_id: "99"
   ```

2. **카테고리 설정**:
   ```yaml
   category:
     name: "PaperReview"
     id: "1329459"
   ```

3. **OpenAI API**:
   ```yaml
   openai:
     api_key: "sk-proj-..."
     model: "gpt-5.2"
     review_model: "gpt-5.2-pro"
   ```

4. **스케줄러 활성화**:
   ```yaml
   schedule:
     enabled: true  # 중요: 스케줄러 활성화
     start_hour: 18
     end_hour: 23
     end_minute: 59
   ```

### 2.4 프롬프트 파일 (선택적)

프롬프트를 커스터마이징했다면:

```bash
# prompts.yaml이 있다면 복사 (없으면 기본값 사용)
# cp prompts.yaml.example prompts.yaml  # 필요시
```

### 2.5 논문 리스트 수집 (선택적)

처음 실행하기 전에 논문 리스트를 수집할 수 있습니다:

```bash
# 논문 수집 (시간이 걸릴 수 있음)
docker compose run --rm tistory-writer python scripts/collect_papers.py
```

또는 나중에 자동으로 수집하도록 할 수도 있습니다.

### 2.6 Docker 컨테이너 실행

```bash
# Docker 이미지 빌드 및 실행
docker compose up -d --build

# 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f
```

### 2.7 systemd 서비스 등록 (선택적, 권장)

서버 재부팅 후에도 자동으로 실행되도록:

```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/tistory-writer.service
```

다음 내용 입력:

```ini
[Unit]
Description=Tistory Auto Poster
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/Tistory_writer
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

서비스 활성화:

```bash
# 경로를 실제 프로젝트 경로로 변경한 후
sudo systemctl daemon-reload
sudo systemctl enable tistory-writer.service
sudo systemctl start tistory-writer.service
sudo systemctl status tistory-writer.service
```

## 3. 업데이트 방법

코드를 업데이트한 후:

```bash
# 1. GitHub에 푸시
git add .
git commit -m "Update: ..."
git push origin main

# 2. 서버에서 업데이트
cd /opt/Tistory_writer
git pull origin main

# 3. Docker 이미지 재빌드
docker compose up -d --build

# 4. 상태 확인
docker compose logs -f
```

## 4. 모니터링 및 관리

### 로그 확인

```bash
# 실시간 로그
docker compose logs -f

# 최근 100줄
docker compose logs --tail=100

# 컨테이너 내부 로그 파일
docker compose exec tistory-writer tail -f /app/data/tistory_poster.log
```

### 상태 확인

```bash
# 컨테이너 상태
docker compose ps

# 논문 개수 확인
docker compose exec tistory-writer cat /app/data/papers.json | head -20

# 진행 상황 확인
docker compose exec tistory-writer cat /app/data/paper_state.json
```

### 수동 글 작성 (테스트용)

```bash
# 스케줄러 비활성화하고 즉시 실행
# config.yaml에서 schedule.enabled: false 로 변경 후:
docker compose restart
docker compose logs -f
```

## 5. 문제 해결

### 컨테이너가 재시작되지 않는 경우

```bash
# 로그 확인
docker compose logs tistory-writer

# 컨테이너 재시작
docker compose restart

# 완전히 재생성
docker compose down
docker compose up -d --build
```

### 스케줄러가 작동하지 않는 경우

1. `config.yaml`에서 `schedule.enabled: true` 확인
2. 로그에서 "스케줄러 모드로 실행합니다..." 메시지 확인
3. 다음 실행 예정 시간이 로그에 표시되는지 확인

### 논문 리스트가 없는 경우

```bash
# 논문 수집
docker compose run --rm tistory-writer python scripts/collect_papers.py
```

## 6. 백업

### 설정 파일 백업

```bash
# 설정 파일 백업
cp config.yaml config.yaml.backup.$(date +%Y%m%d)
```

### 데이터 백업

```bash
# data 디렉토리 백업
tar -czf data_backup_$(date +%Y%m%d).tar.gz data/
```

## 7. 보안 주의사항

1. **config.yaml 권한 설정**:
   ```bash
   chmod 600 config.yaml
   ```

2. **.gitignore 확인**: 민감한 파일이 GitHub에 업로드되지 않았는지 확인:
   ```bash
   git status
   git ls-files | grep -E "(config\.yaml|data/)"
   ```

3. **환경 변수 사용 고려**: 민감한 정보는 환경 변수로 관리할 수도 있습니다 (향후 개선 가능).

