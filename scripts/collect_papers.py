"""
논문 리스트 수집 스크립트
"""
import sys
import yaml
import logging
from pathlib import Path

# src 모듈 import를 위한 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client.claude_client import ClaudeClient
from src.data.paper_manager import PaperManager
from src.data.paper_collector import PaperCollector

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """논문 리스트 수집"""
    try:
        # 설정 파일 로드
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config.yaml"
        if not config_path.exists():
            print("❌ config.yaml 파일을 찾을 수 없습니다.")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Claude API 키 확인
        if 'claude' not in config or not config['claude'].get('api_key'):
            print("❌ Claude API 키가 설정되지 않았습니다. config.yaml에 claude.api_key를 추가해주세요.")
            return

        # Claude 클라이언트 초기화
        prompts_file = config.get('prompts_file', 'prompts.yaml')
        claude_client = ClaudeClient(
            api_key=config['claude']['api_key'],
            model=config['claude'].get('model', 'claude-sonnet-4-20250514'),
            prompts_file=prompts_file
        )

        # 논문 매니저 초기화
        papers_file = project_root / "data/papers.json"
        paper_manager = PaperManager(papers_file=str(papers_file))

        # 논문 수집기 초기화
        collector = PaperCollector(claude_client, paper_manager)
        
        # 논문 수집 설정
        paper_collection_config = config.get('paper_collection', {})
        categories = paper_collection_config.get('categories', [])
        batch_size = paper_collection_config.get('batch_size', 10)
        
        if not categories:
            # 기존 형식 지원 (하위 호환성)
            topic = paper_collection_config.get('topic', 'AI/ML')
            count = paper_collection_config.get('count', 100)
            recent_years = paper_collection_config.get('recent_years', 5)
            categories = [{
                'name': '기본 카테고리',
                'topic': topic,
                'count': count,
                'recent_years': recent_years
            }]
        
        print(f"📚 논문 리스트 수집 시작...")
        print(f"   카테고리 수: {len(categories)}개")
        print(f"   배치 크기: {batch_size}개")
        
        for i, cat in enumerate(categories, 1):
            print(f"   {i}. {cat.get('name', 'N/A')}: {cat.get('count', 0)}개")
        
        print()
        
        # 논문 수집 및 저장 (2단계 프로세스)
        papers = collector.collect_and_save_papers(
            categories=categories,
            batch_size=batch_size
        )
        
        print(f"✅ {len(papers)}개의 논문이 저장되었습니다.")
        print(f"   저장 위치: data/papers.json")
        
        # 상위 5개 논문 출력
        print("\n📋 상위 5개 논문:")
        for i, paper in enumerate(papers[:5], 1):
            print(f"{i}. {paper.get('title', 'N/A')}")
            print(f"   저자: {', '.join(paper.get('authors', [])[:3])}...")
            print(f"   인용수: {paper.get('citations', 'N/A')}, 중요도: {paper.get('importance_score', 'N/A')}")
            print()
        
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        print(f"❌ 오류: {e}")


if __name__ == "__main__":
    main()

