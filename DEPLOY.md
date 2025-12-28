# 리눅스 서버 배포 가이드

리눅스 서버에서 티스토리 자동 포스팅 프로그램을 계속 실행하는 방법입니다.

## 목차

1. [빠른 시작](#빠른-시작)
2. [GitHub에서 배포](#github에서-배포-권장)
3. [스케줄러 설정](#스케줄러-설정)
4. [systemd 서비스로 등록](#systemd-서비스로-등록-권장)
5. [Docker Compose 직접 사용](#docker-compose-직접-사용)
6. [모니터링](#모니터링)
7. [문제 해결](#문제-해결)
8. [업데이트](#업데이트)
9. [백업](#백업)

## 빠른 시작

```bash
# 1. 프로젝트 클론
git clone <your-repo-url>
cd Tistory_writer

# 2. 설정 파일 생성 및 편집
cp config.yaml.example config.yaml
nano config.yaml  # 또는 vi config.yaml

# 3. data 디렉토리 생성 (필수 - 볼륨 마운트를 위해 필요)
mkdir -p data

# 4. 스케줄러 활성화
# config.yaml에서 schedule.enabled: true 로 설정

# 5. Docker 이미지 빌드 (논문 수집을 위해 먼저 빌드)
docker compose build

# 6. 논문 리스트 수집 (필수 - 처음 배포 시 반드시 실행)
docker compose run --rm tistory-writer python scripts/collect_papers.py

# 7. Docker Compose로 실행
docker compose up -d

# 8. 상태 확인
docker compose ps
docker compose logs -f
```

## GitHub에서 배포 (권장)

### 1. GitHub에 코드 업로드

```bash
# Git 초기화 (이미 있으면 생략)
git init

# 원격 저장소 추가
git remote add origin <your-github-repo-url>

# 모든 파일 추가 (config.yaml, data/ 등은 .gitignore에 의해 제외됨)
git add .

# 커밋
git commit -m "Initial commit: Tistory auto poster"

# GitHub에 푸시
git push -u origin main
```

**주의**: `config.yaml`, `prompts.yaml`, `data/` 디렉토리는 `.gitignore`에 포함되어 있어 GitHub에 업로드되지 않습니다. 리눅스 서버에서 직접 생성해야 합니다.

### 2. 리눅스 서버에서 클론 및 설정

```bash
# 1. 프로젝트 클론
cd /opt  # 또는 원하는 디렉토리
git clone <your-github-repo-url> Tistory_writer
cd Tistory_writer

# 2. 설정 파일 생성
cp config.yaml.example config.yaml
cp prompts.yaml.example prompts.yaml  # prompts.yaml이 있다면

# 3. 설정 파일 편집
nano config.yaml
# - tistory.cookies 설정
# - openai.api_key 설정
# - schedule.enabled: true 로 변경
# - 기타 필요한 설정

# 4. data 디렉토리 생성 (필수 - 볼륨 마운트를 위해 필요)
mkdir -p data

# 5. Docker 이미지 빌드 (논문 수집을 위해 먼저 빌드)
docker compose build

# 6. 논문 리스트 수집 (필수 - 처음 배포 시 반드시 실행)
docker compose run --rm tistory-writer python scripts/collect_papers.py

# 7. Docker Compose로 실행
docker compose up -d

# 8. 로그 확인
docker compose logs -f
```

## 스케줄러 설정

`config.yaml`에서 스케줄러를 활성화하세요:

```yaml
schedule:
  enabled: true  # 스케줄러 활성화
  start_hour: 18  # 오후 6시
  end_hour: 23    # 오후 11시
  end_minute: 59  # 59분
```

- `enabled: true`: 매일 지정된 시간 범위에 자동으로 글 작성
- `enabled: false`: 실행할 때마다 바로 글 작성 (테스트용)

스케줄러가 활성화되면 컨테이너가 계속 실행되며, 매일 오후 6시~11시 59분 사이의 랜덤한 시간에 글을 작성합니다.

## systemd 서비스로 등록 (권장)

영구적으로 실행하려면 systemd 서비스로 등록하는 것이 좋습니다.

### 1. 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/tistory-writer.service
```

다음 내용 입력 (경로는 실제 프로젝트 경로로 변경):

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

### 2. 서비스 활성화 및 시작

```bash
# 서비스 파일 리로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable tistory-writer.service

# 서비스 시작
sudo systemctl start tistory-writer.service

# 상태 확인
sudo systemctl status tistory-writer.service
```

### 3. 서비스 관리

```bash
# 서비스 시작
sudo systemctl start tistory-writer.service

# 서비스 중지
sudo systemctl stop tistory-writer.service

# 서비스 재시작
sudo systemctl restart tistory-writer.service

# 서비스 상태 확인
sudo systemctl status tistory-writer.service

# 로그 확인
sudo journalctl -u tistory-writer.service -f
```

## Docker Compose 직접 사용

systemd 서비스를 사용하지 않는 경우:

```bash
# 백그라운드로 실행
docker compose up -d

# 로그 확인
docker compose logs -f

# 중지
docker compose down

# 재시작
docker compose restart
```

## 모니터링

### 로그 확인

```bash
# Docker Compose 로그
docker compose logs -f

# 컨테이너 내부 로그 파일
docker compose exec tistory-writer tail -f /app/data/tistory_poster.log

# systemd 서비스 로그
sudo journalctl -u tistory-writer.service -f
```

### 상태 확인

```bash
# 컨테이너 상태
docker compose ps

# 논문 리스트 확인
docker compose exec tistory-writer cat /app/data/papers.json | jq '.papers | length'

# 진행 상황 확인
docker compose exec tistory-writer cat /app/data/paper_state.json
```

## 문제 해결

### 컨테이너가 계속 재시작되는 경우

```bash
# 로그 확인
docker compose logs tistory-writer

# 컨테이너 내부 진입
docker compose exec tistory-writer /bin/bash

# 설정 파일 확인
docker compose exec tistory-writer cat /app/config.yaml
```

### 스케줄러가 작동하지 않는 경우

1. `config.yaml`에서 `schedule.enabled: true` 확인
2. 로그에서 "스케줄러 모드로 실행합니다..." 메시지 확인
3. 다음 실행 예정 시간 확인

### 논문 리스트가 없는 경우

처음 배포 시 또는 `data/papers.json` 파일이 없는 경우:

```bash
# 논문 수집 스크립트 실행
docker compose run --rm tistory-writer python scripts/collect_papers.py
```

**참고**: 처음 배포할 때는 반드시 논문 수집을 먼저 실행해야 합니다. [빠른 시작](#빠른-시작) 섹션을 참고하세요.

## 업데이트

### GitHub에서 최신 코드 가져오기

```bash
# 1. 코드 업데이트
cd /opt/Tistory_writer
git pull origin main

# 2. Docker 이미지 재빌드
docker compose up -d --build

# 3. 상태 확인
docker compose logs -f
```

### 설정 변경 후 재시작

```bash
# config.yaml 수정 후
docker compose restart
# 또는
docker compose up -d --force-recreate
```

## 백업

### 중요 파일 백업

```bash
# 설정 파일 백업
cp config.yaml config.yaml.backup
cp prompts.yaml prompts.yaml.backup  # 있다면

# 데이터 백업
tar -czf data_backup_$(date +%Y%m%d).tar.gz data/
```

### 정기 백업 스크립트 예시

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/tistory-writer"
DATE=$(date +%Y%m%d)
PROJECT_DIR="/opt/Tistory_writer"

mkdir -p "$BACKUP_DIR"

# 설정 파일 백업
cp "$PROJECT_DIR/config.yaml" "$BACKUP_DIR/config_$DATE.yaml"
cp "$PROJECT_DIR/prompts.yaml" "$BACKUP_DIR/prompts_$DATE.yaml" 2>/dev/null || true

# 데이터 디렉토리 백업
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" -C "$PROJECT_DIR" data/

# 30일 이상 된 백업 삭제
find "$BACKUP_DIR" -name "*.yaml" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

crontab에 등록:

```bash
# 매일 새벽 2시에 백업
0 2 * * * /path/to/backup.sh
```

## 환경 요구사항

- Docker 및 Docker Compose 설치 필요
- 최소 512MB 메모리 권장
- 최소 1GB 디스크 공간 권장

## 보안 고려사항

1. **설정 파일 보호**: `config.yaml`에 API 키 등 민감한 정보가 포함되어 있습니다. 적절한 권한 설정:
   ```bash
   chmod 600 config.yaml
   ```

2. **.gitignore 확인**: 민감한 파일이 GitHub에 업로드되지 않도록 확인:
   - `config.yaml`
   - `prompts.yaml`
   - `data/` 디렉토리

3. **네트워크 보안**: 필요시 방화벽에서 필요한 포트만 열어두세요.

## 참고사항

- **data 디렉토리 필수**: `docker-compose.yml`에서 `./data:/app/data`로 볼륨 마운트하므로, 반드시 호스트에 `data` 디렉토리를 미리 생성해야 합니다 (`mkdir -p data`)
- **논문 리스트 수집 필수**: 처음 배포할 때는 반드시 `docker compose run --rm tistory-writer python scripts/collect_papers.py`를 실행하여 논문 리스트를 수집해야 합니다. `data/papers.json` 파일이 없으면 프로그램이 작동하지 않습니다
- 스케줄러 모드에서는 컨테이너가 계속 실행되어야 합니다 (`restart: unless-stopped` 설정)
- 한국 시간대(`TZ=Asia/Seoul`)로 설정되어 있습니다
- 논문 리스트는 `data/papers.json`에 저장됩니다
- 진행 상황은 `data/paper_state.json`에 저장됩니다
