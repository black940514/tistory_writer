"""
논문 리스트에 수동으로 논문 추가하는 스크립트
"""
import sys
import json
import logging
from pathlib import Path

# src 모듈 import를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.paper_manager import PaperManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_papers_from_file(file_path: str, project_root: Path = None) -> list:
    """파일에서 논문 리스트 로드"""
    if project_root is None:
        project_root = Path(__file__).parent.parent
    papers_file = project_root / file_path if not Path(file_path).is_absolute() else Path(file_path)
    if not papers_file.exists():
        logger.error(f"파일을 찾을 수 없습니다: {file_path}")
        return []
    
    try:
        with open(papers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'papers' in data:
                return data['papers']
            elif isinstance(data, list):
                return data
            else:
                logger.error("잘못된 JSON 형식입니다.")
                return []
    except Exception as e:
        logger.error(f"파일 로드 오류: {e}")
        return []


def main():
    """논문 추가"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python add_papers.py <papers_file.json>")
        print("\n예시:")
        print("  python add_papers.py papers_template.json")
        print("  python add_papers.py custom_papers.json")
        print("\n논문 파일 형식:")
        print('  {"papers": [{"title": "...", "authors": [...], "year": 2024, ...}, ...]}')
        return
    
    papers_file = sys.argv[1]
    project_root = Path(__file__).parent.parent
    
    try:
        # 파일에서 논문 로드
        print(f"📄 논문 파일 로드: {papers_file}")
        new_papers = load_papers_from_file(papers_file, project_root)
        
        if not new_papers:
            print("❌ 논문이 없습니다.")
            return
        
        print(f"✅ {len(new_papers)}개의 논문을 찾았습니다.")
        
        # 논문 매니저 초기화
        project_root = Path(__file__).parent.parent
        papers_file = project_root / "data/papers.json"
        paper_manager = PaperManager(papers_file=str(papers_file))
        
        # 기존 논문 가져오기
        existing_papers = paper_manager.papers
        existing_titles = {p.get('title', '') for p in existing_papers}
        
        # 중복 제거 (제목 기준)
        papers_to_add = []
        for paper in new_papers:
            title = paper.get('title', '')
            if title and title not in existing_titles:
                papers_to_add.append(paper)
            else:
                logger.info(f"중복 논문 건너뜀: {title}")
        
        if not papers_to_add:
            print("❌ 추가할 새 논문이 없습니다 (모두 중복됨).")
            return
        
        print(f"➕ {len(papers_to_add)}개의 새 논문을 추가합니다.")
        
        # 기존 논문과 합치기
        all_papers = existing_papers + papers_to_add
        
        # 중요도 순으로 정렬
        sorted_papers = sorted(
            all_papers,
            key=lambda x: (
                x.get('importance_score', 0) * 10 + x.get('citations', 0)
            ),
            reverse=True
        )
        
        # 저장
        paper_manager.set_papers(sorted_papers)
        
        print(f"✅ 총 {len(sorted_papers)}개의 논문이 저장되었습니다.")
        print(f"   - 기존: {len(existing_papers)}개")
        print(f"   - 추가: {len(papers_to_add)}개")
        print(f"   - 저장 위치: data/papers.json")
        
        # 추가된 논문 목록 출력
        print("\n📋 추가된 논문 목록:")
        for i, paper in enumerate(papers_to_add, 1):
            print(f"{i}. {paper.get('title', 'N/A')}")
            print(f"   저자: {', '.join(paper.get('authors', [])[:3])}")
            print(f"   인용수: {paper.get('citations', 'N/A')}, 중요도: {paper.get('importance_score', 'N/A')}")
            print()
        
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        print(f"❌ 오류: {e}")


if __name__ == "__main__":
    main()

