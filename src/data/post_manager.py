"""
포스트 번호 관리자
"""
import json
import os
from pathlib import Path
from typing import Optional


class PostManager:
    """포스트 번호 및 상태 관리"""
    
    def __init__(self, state_file: str = "data/post_state.json"):
        """
        Args:
            state_file: 상태를 저장할 파일 경로
        """
        self.state_file = Path(state_file)
        # 디렉토리가 없으면 생성
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()
    
    def _load_state(self) -> dict:
        """상태 파일 로드"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"상태 파일 로드 실패: {e}")
                return {'last_number': 0}
        return {'last_number': 0}
    
    def _save_state(self):
        """상태 파일 저장"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"상태 파일 저장 실패: {e}")
    
    def get_next_post_number(self) -> int:
        """다음 포스트 번호 가져오기"""
        next_number = self.state.get('last_number', 0) + 1
        self.state['last_number'] = next_number
        self._save_state()
        return next_number
    
    def get_post_title(self, number: int) -> str:
        """포스트 제목 생성"""
        return f"AI논문 리뷰_{number}"

