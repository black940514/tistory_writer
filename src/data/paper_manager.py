"""
논문 리스트 관리자
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PaperManager:
    """논문 리스트 관리 및 순차 선택"""
    
    def __init__(self, papers_file: str = "data/papers.json", state_file: str = "data/paper_state.json", reset_on_first_run: bool = True):
        """
        Args:
            papers_file: 논문 리스트 저장 파일 경로
            state_file: 현재 진행 상태 저장 파일 경로
            reset_on_first_run: 첫 실행 시 진행 상태 리셋 여부 (기본값: True)
        """
        self.papers_file = Path(papers_file)
        self.state_file = Path(state_file)
        
        # 디렉토리 생성
        self.papers_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.papers = self._load_papers()
        
        # 첫 실행 감지 (state_file이 없거나 빈 경우)
        is_first_run = not self.state_file.exists() or (self.state_file.exists() and self.state_file.stat().st_size == 0)
        
        if is_first_run and reset_on_first_run:
            logger.info("첫 실행 감지: 진행 상태를 초기화합니다.")
            self.state = {'current_index': 0, 'reviewed_papers': [], 'last_processed': None, 'first_run_at': datetime.now().isoformat()}
            self._save_state()
        else:
            self.state = self._load_state()
    
    def _load_papers(self) -> List[Dict]:
        """논문 리스트 로드"""
        if not self.papers_file.exists():
            logger.info(f"논문 리스트 파일이 없습니다: {self.papers_file} (빈 리스트로 시작)")
            return []
        
        try:
            # 파일 크기 확인 (빈 파일 체크)
            file_size = self.papers_file.stat().st_size
            if file_size == 0:
                logger.warning(f"논문 리스트 파일이 비어있습니다: {self.papers_file} (빈 리스트로 시작)")
                return []
            
            with open(self.papers_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logger.warning(f"논문 리스트 파일에 내용이 없습니다: {self.papers_file} (빈 리스트로 시작)")
                    return []
                
                data = json.loads(content)
                papers = data.get('papers', []) if isinstance(data, dict) else data
                
                # papers가 리스트인지 확인
                if not isinstance(papers, list):
                    logger.warning(f"논문 리스트 형식이 올바르지 않습니다 (리스트가 아님): {self.papers_file} (빈 리스트로 시작)")
                    return []
                
                logger.info(f"{len(papers)}개의 논문 로드됨")
                return papers
                
        except json.JSONDecodeError as e:
            logger.warning(f"논문 리스트 JSON 파싱 오류: {e} (파일: {self.papers_file}) - 빈 리스트로 시작")
            return []
        except Exception as e:
            logger.error(f"논문 리스트 로드 실패: {e} (파일: {self.papers_file}) - 빈 리스트로 시작", exc_info=True)
            return []
    
    def _save_papers(self):
        """논문 리스트 저장"""
        try:
            data = {
                'papers': self.papers,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.papers_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"{len(self.papers)}개의 논문 저장됨")
        except Exception as e:
            logger.error(f"논문 리스트 저장 실패: {e}")
    
    def _load_state(self) -> dict:
        """진행 상태 로드"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    # 기존 형식 호환성 유지 (필드가 없으면 기본값 추가)
                    if 'last_processed' not in state:
                        state['last_processed'] = None
                    if 'first_run_at' not in state:
                        state['first_run_at'] = None
                    return state
            except Exception as e:
                logger.error(f"상태 파일 로드 실패: {e}")
                return {'current_index': 0, 'reviewed_papers': [], 'last_processed': None, 'first_run_at': None}
        return {'current_index': 0, 'reviewed_papers': [], 'last_processed': None, 'first_run_at': None}
    
    def _save_state(self):
        """진행 상태 저장 (상세 정보 포함)"""
        try:
            # 저장할 때 통계 정보 추가
            state_to_save = {
                'current_index': self.state.get('current_index', 0),
                'reviewed_papers': self.state.get('reviewed_papers', []),
                'last_processed': self.state.get('last_processed'),
                'first_run_at': self.state.get('first_run_at'),
                'last_updated': datetime.now().isoformat(),
                'statistics': {
                    'total_papers': len(self.papers),
                    'reviewed_count': len(self.state.get('reviewed_papers', [])),
                    'remaining_count': len(self.papers) - len(self.state.get('reviewed_papers', [])),
                    'progress_percent': round((len(self.state.get('reviewed_papers', [])) / len(self.papers) * 100), 2) if self.papers else 0
                }
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"상태 파일 저장 실패: {e}")
    
    def set_papers(self, papers: List[Dict]):
        """
        논문 리스트 설정 및 저장
        
        Args:
            papers: 논문 리스트 (원래 순서 유지)
        """
        # papers.json의 원래 순서 유지 (정렬하지 않음)
        self.papers = papers
        self._save_papers()
        logger.info(f"{len(self.papers)}개의 논문이 원래 순서대로 저장됨")
    
    def get_next_paper(self) -> Optional[Dict]:
        """
        다음 리뷰할 논문 가져오기
        
        Returns:
            논문 정보 또는 None (모든 논문을 리뷰한 경우)
        """
        if not self.papers:
            logger.warning("논문 리스트가 비어있습니다.")
            return None
        
        current_index = self.state.get('current_index', 0)
        reviewed_papers = self.state.get('reviewed_papers', [])
        
        # 아직 리뷰하지 않은 논문 찾기
        for i in range(current_index, len(self.papers)):
            paper = self.papers[i]
            paper_id = self._get_paper_id(paper)
            
            if paper_id not in reviewed_papers:
                # 상태 업데이트 (마지막 처리 논문 정보 추가)
                self.state['current_index'] = i + 1
                self.state['reviewed_papers'].append(paper_id)
                self.state['last_processed'] = {
                    'paper_id': paper_id,
                    'title': paper.get('title', 'N/A'),
                    'index': i,
                    'processed_at': datetime.now().isoformat()
                }
                self._save_state()
                
                logger.info(f"다음 논문 선택: {paper.get('title', 'N/A')} (인덱스: {i})")
                return paper
        
        # 모든 논문을 리뷰한 경우
        logger.info("모든 논문을 리뷰했습니다. 처음부터 다시 시작합니다.")
        self.state['current_index'] = 0
        self.state['reviewed_papers'] = []
        self._save_state()
        
        # 처음 논문 반환
        if self.papers:
            paper = self.papers[0]
            paper_id = self._get_paper_id(paper)
            self.state['current_index'] = 1
            self.state['reviewed_papers'].append(paper_id)
            self._save_state()
            return paper
        
        return None
    
    def _get_paper_id(self, paper: Dict) -> str:
        """논문 고유 ID 생성"""
        title = paper.get('title', '')
        year = paper.get('year', '')
        return f"{title}_{year}"
    
    def mark_paper_reviewed(self, paper: Dict):
        """
        논문을 리뷰 완료로 표시
        
        Args:
            paper: 논문 정보
        """
        paper_id = self._get_paper_id(paper)
        if paper_id not in self.state.get('reviewed_papers', []):
            self.state.setdefault('reviewed_papers', []).append(paper_id)
            self._save_state()
            logger.info(f"논문 리뷰 완료 표시: {paper.get('title', 'N/A')}")
    
    def get_paper_count(self) -> int:
        """전체 논문 개수"""
        return len(self.papers)
    
    def get_reviewed_count(self) -> int:
        """리뷰 완료된 논문 개수"""
        return len(self.state.get('reviewed_papers', []))
    
    def reset_progress(self):
        """진행 상태 초기화 (모든 논문을 다시 리뷰하도록)"""
        self.state = {
            'current_index': 0,
            'reviewed_papers': [],
            'last_processed': None,
            'first_run_at': datetime.now().isoformat()
        }
        self._save_state()
        logger.info("진행 상태가 초기화되었습니다.")
    
    def get_progress_info(self) -> Dict:
        """진행 상태 정보 반환 (추적용)"""
        last_processed = self.state.get('last_processed')
        return {
            'current_index': self.state.get('current_index', 0),
            'total_papers': len(self.papers),
            'reviewed_count': len(self.state.get('reviewed_papers', [])),
            'remaining_count': len(self.papers) - len(self.state.get('reviewed_papers', [])),
            'progress_percent': round((len(self.state.get('reviewed_papers', [])) / len(self.papers) * 100), 2) if self.papers else 0,
            'last_processed': last_processed,
            'first_run_at': self.state.get('first_run_at'),
            'last_updated': self.state.get('last_updated')
        }

    def get_all_papers(self) -> List[Dict]:
        """전체 논문 리스트 반환"""
        return self.papers

    def get_paper_by_index(self, index: int) -> Optional[Dict]:
        """
        특정 인덱스의 논문 반환

        Args:
            index: 논문 인덱스 (0부터 시작)

        Returns:
            논문 정보 또는 None
        """
        if 0 <= index < len(self.papers):
            return self.papers[index]
        return None

    def get_unreviewed_papers(self) -> List[Dict]:
        """
        아직 리뷰하지 않은 논문 리스트 반환

        Returns:
            미리뷰 논문 리스트 (인덱스 포함)
        """
        reviewed_papers = self.state.get('reviewed_papers', [])
        unreviewed = []
        for i, paper in enumerate(self.papers):
            paper_id = self._get_paper_id(paper)
            if paper_id not in reviewed_papers:
                paper_with_index = paper.copy()
                paper_with_index['_index'] = i
                unreviewed.append(paper_with_index)
        return unreviewed

    def get_paper_for_post(self, index: int = None) -> Optional[Dict]:
        """
        발행할 논문 가져오기 (인덱스 지정 또는 자동 선택)

        Args:
            index: 논문 인덱스 (None이면 다음 미리뷰 논문 자동 선택)

        Returns:
            논문 정보 또는 None
        """
        if index is not None:
            paper = self.get_paper_by_index(index)
            if paper:
                # 상태 업데이트
                paper_id = self._get_paper_id(paper)
                if paper_id not in self.state.get('reviewed_papers', []):
                    self.state.setdefault('reviewed_papers', []).append(paper_id)
                self.state['last_processed'] = {
                    'paper_id': paper_id,
                    'title': paper.get('title', 'N/A'),
                    'index': index,
                    'processed_at': datetime.now().isoformat()
                }
                self._save_state()
                logger.info(f"지정된 논문 선택: {paper.get('title', 'N/A')} (인덱스: {index})")
                return paper
            return None
        else:
            return self.get_next_paper()

    def is_paper_reviewed(self, paper: Dict) -> bool:
        """논문이 이미 리뷰되었는지 확인"""
        paper_id = self._get_paper_id(paper)
        return paper_id in self.state.get('reviewed_papers', [])

