#!/usr/bin/env python3
"""
간단한 단일 논문 리뷰 생성기
사용법: python simple_review.py "논문제목 또는 arXiv URL"
"""
import sys
import os

# 프로젝트 루트 경로 설정
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 경우
    exe_dir = os.path.dirname(sys.executable)

    # 앱 번들(.app) vs 폴더 모드 구분
    if exe_dir.endswith('MacOS'):
        # 앱 번들: Contents/MacOS -> Contents/Resources
        project_root = os.path.join(os.path.dirname(exe_dir), 'Resources')
        output_dir = os.path.dirname(os.path.dirname(os.path.dirname(exe_dir)))  # .app 밖에 output 생성
    else:
        # 폴더 모드: _internal 폴더
        project_root = os.path.join(exe_dir, '_internal')
        output_dir = exe_dir
else:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = None  # 기본값 사용

sys.path.insert(0, project_root)
os.chdir(project_root)

from scripts.generate_single_output import generate_single_output

def main():
    if len(sys.argv) < 2:
        print("=" * 50)
        print("논문 리뷰 생성기")
        print("=" * 50)
        paper_input = input("\n논문 제목 또는 arXiv URL 입력: ").strip()
        if not paper_input:
            print("입력이 없습니다.")
            sys.exit(1)
    else:
        paper_input = sys.argv[1]

    print(f"\n논문 리뷰 생성 중: {paper_input}\n")

    try:
        filepath = generate_single_output(paper_input, output_dir_override=output_dir)
        if filepath:
            print(f"\n✓ 완료: {filepath}")
        else:
            print("\n✗ 생성 실패")
            sys.exit(1)
    except Exception as e:
        print(f"\n오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
