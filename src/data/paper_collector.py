"""
논문 리스트 수집기 (Claude 활용)
"""
import logging
from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    from ..client.claude_client import ClaudeClient
    from .paper_manager import PaperManager

logger = logging.getLogger(__name__)


class PaperCollector:
    """논문 리스트 수집 및 관리"""

    def __init__(self, claude_client: "ClaudeClient", paper_manager: "PaperManager"):
        """
        Args:
            claude_client: Claude 클라이언트
            paper_manager: 논문 매니저
        """
        self.claude_client = claude_client
        self.paper_manager = paper_manager
    
    def collect_and_save_papers(
        self,
        categories: List[Dict],
        batch_size: int = 10
    ):
        """
        카테고리별로 논문 리스트 수집 및 저장 (2단계 프로세스)
        
        Args:
            categories: 카테고리 설정 리스트
                [
                    {
                        "name": "카테고리 이름",
                        "topic": "주제",
                        "count": 50,
                        "recent_years": 7
                    },
                    ...
                ]
            batch_size: 한 번에 요청할 논문 개수 (기본값: 10개)
        """
        try:
            all_papers = []
            seen_titles = set()  # 전체 중복 제거를 위한 제목 집합
            
            for category_idx, category in enumerate(categories, 1):
                name = category.get('name', f'카테고리 {category_idx}')
                topic = category.get('topic', 'AI/ML')
                count = category.get('count', 50)
                recent_years = category.get('recent_years', 5)
                
                logger.info(f"\n{'='*60}")
                logger.info(f"카테고리 {category_idx}/{len(categories)}: {name}")
                logger.info(f"  주제: {topic}")
                logger.info(f"  목표 개수: {count}개")
                logger.info(f"  최근 {recent_years}년")
                logger.info(f"{'='*60}\n")
                
                category_seen_titles = set(seen_titles)  # 현재 카테고리용 중복 제거
                
                # 1단계: 제목 리스트 수집 (전체 개수 한 번에 요청)
                exclude_titles = list(category_seen_titles)
                logger.info(f"[1단계] {name} - {count}개 논문 제목 요청 중... (이미 {len(exclude_titles)}개 제외)")
                
                try:
                    # 제목만 한 번에 요청
                    category_titles = self.claude_client.generate_paper_list_titles_only(
                topic=topic,
                count=count,
                        recent_years=recent_years,
                        exclude_titles=exclude_titles
            )
                    
                    # 중복 제거 및 정리
                    unique_titles = []
                    for title in category_titles:
                        title_lower = title.strip().lower()
                        if title_lower and title_lower not in category_seen_titles:
                            category_seen_titles.add(title_lower)
                            unique_titles.append(title.strip())
                    
                    # 필요한 개수만큼만 사용
                    category_titles = unique_titles[:count]
                    logger.info(f"[1단계] {name} 완료: {len(category_titles)}개 논문 제목 수집")
                    
                except Exception as e:
                    logger.error(f"[1단계] {name} 오류: {e}", exc_info=True)
                    category_titles = []
                
                if not category_titles:
                    logger.warning(f"[2단계] {name} - 제목이 없어 건너뜁니다.")
                    continue
                
                # 2단계: 상세 정보 요청 (10개씩 배치로 나눠서 요청)
                logger.info(f"\n[2단계] {name} - {len(category_titles)}개 논문의 상세 정보 요청 중...")
                
                detailed_papers = []
                detail_batch_size = 10  # 상세 정보는 한 번에 10개씩
                
                for i in range(0, len(category_titles), detail_batch_size):
                    batch_titles = category_titles[i:i + detail_batch_size]
                    batch_num = (i // detail_batch_size) + 1
                    total_batches = (len(category_titles) + detail_batch_size - 1) // detail_batch_size
                    
                    logger.info(f"[2단계] {name} - 배치 {batch_num}/{total_batches}: {len(batch_titles)}개 논문 상세 정보 요청 중...")
                    
                    try:
                        batch_details = self.claude_client.generate_paper_details(batch_titles)
                        detailed_papers.extend(batch_details)
                        logger.info(f"[2단계] 배치 {batch_num} 완료: {len(batch_details)}개 논문 상세 정보 추가")
                        
                    except Exception as e:
                        logger.warning(f"[2단계] 배치 {batch_num} 오류 (계속 진행): {e}", exc_info=True)
                        continue
                
                # 전체 중복 제거
                final_category_papers = []
                for paper in detailed_papers:
                    title = paper.get('title', '').strip().lower()
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        final_category_papers.append(paper)
                
                all_papers.extend(final_category_papers)
                logger.info(f"\n✅ {name} 완료: {len(final_category_papers)}개 논문 수집 (전체 누적: {len(all_papers)}개)\n")
            
            # 논문 매니저에 저장
            self.paper_manager.set_papers(all_papers)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"전체 수집 완료: {len(all_papers)}개의 논문이 저장되었습니다.")
            logger.info(f"{'='*60}\n")
            
            return all_papers
            
        except Exception as e:
            logger.error(f"논문 리스트 수집 오류: {e}", exc_info=True)
            raise
