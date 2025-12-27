# 사용법 가이드

## 실행 모드

프로그램은 두 가지 실행 모드를 지원합니다:

### 1. 자동 실행 모드 (스케줄러 활성화) - 기본값

매일 지정된 시간에 자동으로 글을 작성합니다.

**설정 방법:**
```yaml
# config.yaml
schedule:
  enabled: true   # 스케줄러 활성화
  start_hour: 18  # 오후 6시
  end_hour: 23    # 오후 11시
  end_minute: 59  # 59분
```

**실행:**
```bash
# Docker로 실행 (백그라운드)
docker compose up -d

# 로그 확인
docker compose logs -f

# 중지
docker compose down
```

이 모드에서는:
- 컨테이너가 계속 실행됩니다
- 매일 오후 6시~11시 59분 사이의 랜덤한 시간에 자동으로 글을 작성합니다
- 다음 실행 예정 시간이 로그에 표시됩니다

### 2. 수동 실행 모드 (스케줄러 비활성화)

실행할 때마다 바로 글을 작성하고 종료합니다.

**설정 방법:**
```yaml
# config.yaml
schedule:
  enabled: false  # 스케줄러 비활성화
```

**실행 방법:**

**방법 1: Docker 사용**
```bash
# 한 번 실행
docker compose up

# 또는 백그라운드로 실행
docker compose up -d
docker compose logs -f
```

**방법 2: Python 직접 실행**
```bash
python scripts/main.py
```

이 모드에서는:
- 글을 한 번 작성하고 프로그램이 종료됩니다
- Docker를 사용하는 경우, 컨테이너도 종료됩니다

## 모드 전환

### 자동 실행 모드 → 수동 실행 모드

1. `config.yaml` 파일 수정:
   ```yaml
   schedule:
     enabled: false
   ```

2. 실행:
   ```bash
   docker compose up
   ```

### 수동 실행 모드 → 자동 실행 모드

1. `config.yaml` 파일 수정:
   ```yaml
   schedule:
     enabled: true
   ```

2. 실행:
   ```bash
   docker compose up -d
   ```

## 권장 설정

- **서버에서 계속 실행하고 싶을 때**: `schedule.enabled: true` + `docker compose up -d`
- **테스트하거나 수동으로 글을 쓰고 싶을 때**: `schedule.enabled: false` + `docker compose up` 또는 `python scripts/main.py`

