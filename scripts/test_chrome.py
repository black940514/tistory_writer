#!/usr/bin/env python3
"""
Chrome 및 ChromeDriver 테스트 스크립트
"""
import sys
import subprocess
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("Chrome 및 ChromeDriver 테스트")
print("=" * 70)

# 1. Chrome 버전 확인
print("\n1. Chrome 버전 확인:")
chrome_paths = ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable']
chrome_found = False
for path in chrome_paths:
    if os.path.exists(path):
        try:
            result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
            print(f"  ✓ {path}: {result.stdout.strip()}")
            chrome_found = True
        except Exception as e:
            print(f"  ✗ {path}: 실행 실패 - {e}")
if not chrome_found:
    print("  ✗ Chrome을 찾을 수 없습니다")

# 2. ChromeDriver 버전 확인
print("\n2. ChromeDriver 버전 확인:")
chromedriver_paths = ['/usr/local/bin/chromedriver', '/usr/bin/chromedriver']
chromedriver_found = False
for path in chromedriver_paths:
    if os.path.exists(path):
        try:
            result = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=5)
            print(f"  ✓ {path}: {result.stdout.strip()}")
            chromedriver_found = True
        except Exception as e:
            print(f"  ✗ {path}: 실행 실패 - {e}")
if not chromedriver_found:
    print("  ✗ ChromeDriver를 찾을 수 없습니다")

# 3. Chrome 직접 실행 테스트 (--headless)
print("\n3. Chrome 직접 실행 테스트 (--headless --no-sandbox):")
if chrome_found:
    chrome_path = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_path = path
            break
    if chrome_path:
        try:
            result = subprocess.run(
                [chrome_path, '--headless', '--no-sandbox', '--disable-gpu', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  ✓ Chrome 실행 성공")
            else:
                print(f"  ✗ Chrome 실행 실패 (exit code: {result.returncode})")
                print(f"    stderr: {result.stderr[:500]}")
        except Exception as e:
            print(f"  ✗ Chrome 실행 중 오류: {e}")

# 4. 디렉토리 권한 확인
print("\n4. 디렉토리 권한 확인:")
cache_dir = '/app/.cache/selenium'
chrome_data_dir = f'{cache_dir}/chrome'
for dir_path in [cache_dir, chrome_data_dir]:
    if os.path.exists(dir_path):
        stat = os.stat(dir_path)
        print(f"  {dir_path}:")
        print(f"    존재: ✓")
        print(f"    권한: {oct(stat.st_mode)[-3:]}")
        print(f"    소유자: {stat.st_uid}:{stat.st_gid}")
        # 쓰기 권한 확인
        if os.access(dir_path, os.W_OK):
            print(f"    쓰기 권한: ✓")
        else:
            print(f"    쓰기 권한: ✗")
    else:
        print(f"  {dir_path}: 존재하지 않음")

# 5. 환경 변수 확인
print("\n5. 환경 변수 확인:")
env_vars = ['HOME', 'SELENIUM_CACHE_DIR']
for var in env_vars:
    value = os.environ.get(var, '설정되지 않음')
    print(f"  {var}: {value}")

print("\n" + "=" * 70)

