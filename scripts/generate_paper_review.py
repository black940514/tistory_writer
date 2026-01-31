"""
논문 리뷰 생성 및 관리 프로그램
논문명, arXiv 주소 등을 입력받아 MD 파일 생성 및 작성 이력 관리
"""
import sys
import yaml
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

# 프로젝트 루트 경로
from scripts.get_project_root import get_project_root
project_root = get_project_root()

# src 모듈 import를 위한 경로 추가
sys.path.insert(0, str(project_root))

from scripts.generate_single_output import (
    generate_single_output,
    extract_arxiv_id,
    sanitize_filename
)

# 로그 디렉토리 생성
log_dir = project_root / 'data'
log_dir.mkdir(exist_ok=True)

# 작성 이력 파일
REVIEW_HISTORY_FILE = project_root / 'data' / 'review_history.json'

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'paper_review_manager.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ReviewHistoryManager:
    """작성한 논문 리뷰 이력 관리"""
    
    def __init__(self, history_file: Path = REVIEW_HISTORY_FILE):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)  # 디렉토리 생성
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """이력 파일 로드"""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('reviews', [])
        except Exception as e:
            logger.error(f"이력 파일 로드 실패: {e}")
            return []
    
    def _save_history(self):
        """이력 파일 저장"""
        try:
            data = {
                'reviews': self.history,
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self.history)
            }
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"이력 파일 저장 실패: {e}")
    
    def add_review(self, paper_info: Dict, output_file: str):
        """작성 이력 추가"""
        review_entry = {
            'paper_title': paper_info.get('title', 'N/A'),
            'arxiv_id': paper_info.get('arxiv_id'),
            'url': paper_info.get('url'),
            'authors': paper_info.get('authors', []),
            'year': paper_info.get('year'),
            'output_file': output_file,
            'created_at': datetime.now().isoformat()
        }
        
        # 중복 체크
        if self.is_duplicate(paper_info):
            logger.warning(f"이미 작성된 논문입니다: {paper_info.get('title', 'N/A')}")
            return False
        
        self.history.append(review_entry)
        self._save_history()
        logger.info(f"작성 이력 추가됨: {paper_info.get('title', 'N/A')}")
        return True
    
    def is_duplicate(self, paper_info: Dict) -> bool:
        """중복 체크"""
        title = paper_info.get('title', '').lower().strip()
        arxiv_id = paper_info.get('arxiv_id')
        url = paper_info.get('url')
        
        for review in self.history:
            # 제목으로 중복 체크
            if review.get('paper_title', '').lower().strip() == title:
                return True
            
            # arXiv ID로 중복 체크
            if arxiv_id and review.get('arxiv_id') == arxiv_id:
                return True
            
            # URL로 중복 체크
            if url and review.get('url') == url:
                return True
        
        return False
    
    def list_reviews(self, limit: Optional[int] = None) -> List[Dict]:
        """작성 이력 목록 반환 (최신순)"""
        reviews = sorted(
            self.history,
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )
        
        if limit:
            return reviews[:limit]
        return reviews
    
    def get_review_count(self) -> int:
        """작성한 리뷰 개수"""
        return len(self.history)
    
    def search_reviews(self, query: str) -> List[Dict]:
        """검색 (제목, 저자, arXiv ID)"""
        query_lower = query.lower()
        results = []
        
        for review in self.history:
            # 제목 검색
            if query_lower in review.get('paper_title', '').lower():
                results.append(review)
                continue
            
            # arXiv ID 검색
            if review.get('arxiv_id') and query_lower in review.get('arxiv_id', '').lower():
                results.append(review)
                continue
            
            # 저자 검색
            authors = review.get('authors', [])
            if any(query_lower in author.lower() for author in authors):
                results.append(review)
                continue
        
        return results
    
    def remove_review(self, index: int) -> bool:
        """인덱스로 리뷰 삭제"""
        if 0 <= index < len(self.history):
            removed = self.history.pop(index)
            self._save_history()
            logger.info(f"리뷰 삭제됨: {removed.get('paper_title', 'N/A')}")
            return True
        return False


def create_review(input_str: str, config_path: Optional[str] = None, output_filename: Optional[str] = None) -> Optional[str]:
    """리뷰 생성 및 이력 관리"""
    history_manager = ReviewHistoryManager()
    
    # 논문 정보 가져오기 (중복 체크용)
    arxiv_id = extract_arxiv_id(input_str)
    paper_info_for_check = {'title': input_str, 'arxiv_id': arxiv_id, 'url': None}
    
    if arxiv_id:
        from scripts.generate_single_output import fetch_arxiv_paper_info
        arxiv_info = fetch_arxiv_paper_info(arxiv_id)
        if arxiv_info:
            paper_info_for_check = arxiv_info
    
    # 중복 체크
    if history_manager.is_duplicate(paper_info_for_check):
        print(f"⚠️  이미 작성된 논문입니다!")
        print(f"   제목: {paper_info_for_check.get('title', 'N/A')}")
        response = input("그래도 다시 작성하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            return None
    
    # 리뷰 생성
    filepath = generate_single_output(
        input_str=input_str,
        config_path=config_path,
        output_filename=output_filename
    )
    
    if filepath:
        # 이력 추가
        final_paper_info = paper_info_for_check.copy()
        if arxiv_id:
            final_paper_info['arxiv_id'] = arxiv_id
        
        history_manager.add_review(final_paper_info, filepath)
        print(f"\n✓ 리뷰 생성 완료: {filepath}")
        return filepath
    
    return None


def list_reviews(limit: Optional[int] = None, search: Optional[str] = None):
    """작성 이력 목록 출력"""
    history_manager = ReviewHistoryManager()
    
    if search:
        reviews = history_manager.search_reviews(search)
        print(f"\n🔍 검색 결과: '{search}' ({len(reviews)}개)")
    else:
        reviews = history_manager.list_reviews(limit=limit)
        total = history_manager.get_review_count()
        print(f"\n📝 작성한 리뷰 목록 (총 {total}개)")
    
    if not reviews:
        print("작성한 리뷰가 없습니다.")
        return
    
    print("-" * 80)
    for i, review in enumerate(reviews, 1):
        title = review.get('paper_title', 'N/A')
        arxiv_id = review.get('arxiv_id', 'N/A')
        year = review.get('year', 'N/A')
        created_at = review.get('created_at', '')
        
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_str = dt.strftime('%Y-%m-%d %H:%M')
            except:
                created_str = created_at[:10]
        else:
            created_str = 'N/A'
        
        print(f"{i}. {title}")
        print(f"   arXiv: {arxiv_id} | Year: {year} | 작성일: {created_str}")
        print(f"   파일: {review.get('output_file', 'N/A')}")
        print()


def show_statistics():
    """통계 정보 출력"""
    history_manager = ReviewHistoryManager()
    reviews = history_manager.list_reviews()
    
    total = len(reviews)
    
    if total == 0:
        print("작성한 리뷰가 없습니다.")
        return
    
    # 년도별 통계
    year_counts = {}
    for review in reviews:
        year = review.get('year')
        if year:
            year_counts[year] = year_counts.get(year, 0) + 1
    
    print(f"\n📊 작성 통계")
    print("=" * 50)
    print(f"총 작성 개수: {total}개")
    
    if year_counts:
        print(f"\n년도별 분포:")
        for year in sorted(year_counts.keys(), reverse=True):
            print(f"  {year}년: {year_counts[year]}개")
    
    # 최근 작성 (5개)
    print(f"\n최근 작성 (5개):")
    for i, review in enumerate(reviews[:5], 1):
        title = review.get('paper_title', 'N/A')
        created_at = review.get('created_at', '')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_str = dt.strftime('%Y-%m-%d')
            except:
                created_str = created_at[:10]
        else:
            created_str = 'N/A'
        
        print(f"  {i}. {title[:60]}... ({created_str})")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='논문 리뷰 생성 및 관리 프로그램',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 새 리뷰 생성
  python scripts/generate_paper_review.py create "Attention Is All You Need"
  python scripts/generate_paper_review.py create "https://arxiv.org/abs/1706.03762"
  
  # 리스트 조회
  python scripts/generate_paper_review.py list
  python scripts/generate_paper_review.py list --limit 10
  
  # 검색
  python scripts/generate_paper_review.py search "transformer"
  
  # 통계
  python scripts/generate_paper_review.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='명령어')
    
    # create 명령어
    create_parser = subparsers.add_parser('create', help='새 리뷰 생성')
    create_parser.add_argument('input', type=str, help='논문 제목 또는 arXiv URL')
    create_parser.add_argument('--config', type=str, default=None, help='설정 파일 경로')
    create_parser.add_argument('--output', type=str, default=None, help='출력 파일명')
    
    # list 명령어
    list_parser = subparsers.add_parser('list', help='작성한 리뷰 목록 조회')
    list_parser.add_argument('--limit', type=int, default=None, help='출력 개수 제한')
    
    # search 명령어
    search_parser = subparsers.add_parser('search', help='리뷰 검색')
    search_parser.add_argument('query', type=str, help='검색어 (제목, 저자, arXiv ID)')
    
    # stats 명령어
    stats_parser = subparsers.add_parser('stats', help='통계 정보 조회')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'create':
            create_review(args.input, args.config, args.output)
        
        elif args.command == 'list':
            list_reviews(limit=args.limit)
        
        elif args.command == 'search':
            list_reviews(search=args.query)
        
        elif args.command == 'stats':
            show_statistics()
    
    except KeyboardInterrupt:
        logger.info("프로그램을 종료합니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

