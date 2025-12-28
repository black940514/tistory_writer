"""
논문 리뷰 진행 상태 확인 및 리셋 스크립트
"""
import sys
import json
from pathlib import Path

# 프로젝트 루트 경로
project_root = Path(__file__).parent.parent

# src 모듈 import를 위한 경로 추가
sys.path.insert(0, str(project_root))

from src.data.paper_manager import PaperManager

def main():
    """진행 상태 확인 및 리셋"""
    paper_manager = PaperManager(
        papers_file=str(project_root / "data/papers.json"),
        state_file=str(project_root / "data/paper_state.json")
    )
    
    total_papers = paper_manager.get_paper_count()
    reviewed_count = paper_manager.get_reviewed_count()
    current_index = paper_manager.state.get('current_index', 0)
    
    print("=" * 60)
    print("📊 현재 진행 상태")
    print("=" * 60)
    print(f"전체 논문 수: {total_papers}개")
    print(f"리뷰 완료: {reviewed_count}개")
    print(f"현재 인덱스: {current_index}")
    print(f"진행률: {reviewed_count / total_papers * 100:.1f}%" if total_papers > 0 else "진행률: 0%")
    print(f"남은 논문: {total_papers - reviewed_count}개")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("\n⚠️  진행 상태를 초기화합니다...")
        paper_manager.reset_progress()
        print("✅ 진행 상태가 초기화되었습니다!")
        print("   다음 실행부터 첫 번째 논문부터 다시 시작합니다.")
    else:
        print("\n💡 진행 상태를 리셋하려면:")
        print("   python scripts/reset_progress.py --reset")
        print("\n또는")
        print("   python3 scripts/reset_progress.py --reset")

if __name__ == "__main__":
    main()

