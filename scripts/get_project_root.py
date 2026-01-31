"""
프로젝트 루트 경로를 올바르게 가져오는 유틸리티
PyInstaller로 빌드된 앱 번들에서도 작동
"""
import sys
from pathlib import Path


def get_project_root() -> Path:
    """
    프로젝트 루트 경로 반환

    Returns:
        프로젝트 루트 Path 객체
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행 파일인 경우
        exe_dir = Path(sys.executable).parent

        # 앱 번들(.app) vs 폴더 모드 구분
        if str(exe_dir).endswith('MacOS'):
            # 앱 번들: Contents/MacOS -> Contents/Resources
            return exe_dir.parent / 'Resources'
        else:
            # 폴더 모드: _internal 폴더
            return exe_dir / '_internal'
    else:
        # 일반 Python 스크립트로 실행하는 경우
        # 이 파일의 위치를 기준으로 프로젝트 루트 찾기
        current_file = Path(__file__).resolve()
        # scripts 폴더의 부모가 프로젝트 루트
        return current_file.parent.parent

