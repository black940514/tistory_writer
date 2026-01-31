"""
모든 논문에 대해 본문을 생성하고 output 폴더에 저장
스케줄러 없이 모든 논문을 일괄 처리
"""
import sys
import yaml
import logging
import re
from pathlib import Path
from typing import Dict, List

# 프로젝트 루트 경로
project_root = Path(__file__).parent.parent

# src 모듈 import를 위한 경로 추가
sys.path.insert(0, str(project_root))

from src.content.content_generator import generate_paper_review_content
from src.client.claude_client import ClaudeClient
from src.data.paper_manager import PaperManager
from src.content.image_finder import ImageFinder, insert_images_to_content

# 로그 디렉토리 생성
log_dir = project_root / 'data'
log_dir.mkdir(exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'output_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """
    논문 제목을 안전한 파일명으로 변환
    
    Args:
        title: 논문 제목
        max_length: 최대 파일명 길이
    
    Returns:
        안전한 파일명 (확장자 제외)
    """
    # 특수문자 제거 및 공백을 언더스코어로 변경
    # 파일명으로 사용할 수 없는 문자 제거
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    
    # 너무 길면 자르기
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    # 양쪽 공백 제거
    filename = filename.strip('_')
    
    # 빈 문자열이면 기본값
    if not filename:
        filename = "paper"
    
    return filename


def extract_abbreviation(paper_title: str) -> str:
    """
    논문 제목에서 약어 추출 (main.py의 로직 재사용)
    """
    # 1. 제목 앞에 [XXX] 형식이 있으면 추출
    bracket_match = re.match(r'\[([^\]]+)\]\s*(.+)', paper_title)
    if bracket_match:
        return bracket_match.group(1)
    
    title_lower = paper_title.lower()
    title_words = paper_title.split()
    
    # 2. 알려진 약어 사전
    abbreviation_patterns = [
        (['vision transformer', 'an image is worth', 'image is worth 16x16'], 'ViT'),
        (['swin transformer'], 'Swin'),
        (['transformer', 'attention is all you need'], 'Transformer'),
        (['convnext', 'convnet for the'], 'ConvNeXt'),
        (['swav', 'swapping assignments'], 'SwAV'),
        (['simclr', 'simple framework for contrastive'], 'SimCLR'),
        (['moco', 'momentum contrast'], 'MoCo'),
        (['byol', 'bootstrap your own'], 'BYOL'),
        (['dino', 'knowledge distillation'], 'DINO'),
        (['mae', 'masked autoencoder'], 'MAE'),
        (['beit', 'bert pre-training'], 'BEiT'),
        (['clip', 'natural language supervision'], 'CLIP'),
        (['blip', 'bootstrapping language-image'], 'BLIP'),
        (['detr', 'end-to-end object detection'], 'DETR'),
        (['yolo'], 'YOLO'),
        (['mask r-cnn', 'mask rcnn'], 'Mask R-CNN'),
        (['segment anything', 'sam'], 'SAM'),
        (['diffusion'], 'DDPM'),
        (['latent diffusion', 'ldm'], 'LDM'),
        (['stable diffusion'], 'Stable Diffusion'),
        (['gan', 'generative adversarial'], 'GAN'),
        (['nerf', 'neural radiance fields'], 'NeRF'),
        (['gpt'], 'GPT'),
        (['bert', 'bidirectional encoder'], 'BERT'),
        (['llama'], 'LLaMA'),
        (['sora'], 'Sora'),
        (['resnet', 'residual learning'], 'ResNet'),
        (['efficientnet'], 'EfficientNet'),
    ]
    
    for keywords, abbrev in abbreviation_patterns:
        for keyword in keywords:
            if keyword in title_lower:
                return abbrev
    
    # 3. 제목에서 약어 추출 시도
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    important_words = [w for w in title_words if w and w[0].isupper() and w.lower() not in stop_words]
    
    if len(important_words) >= 2:
        abbrev_candidates = []
        for word in important_words[:4]:
            if len(word) <= 6 and word.isupper():
                abbrev_candidates.append(word)
            else:
                abbrev_candidates.append(word[0].upper())
        
        if abbrev_candidates:
            abbrev = ''.join(abbrev_candidates[:4])
            if len(abbrev) > 4:
                abbrev = abbrev[:4]
            if len(abbrev) >= 2:
                return abbrev
    
    # 4. 첫 단어 확인
    if title_words:
        first_word = title_words[0]
        if first_word.isupper() and 2 <= len(first_word) <= 6:
            return first_word
        caps_only = ''.join([c for c in first_word if c.isupper()])
        if len(caps_only) >= 2 and len(caps_only) <= 4:
            return caps_only
    
    return title_words[0] if title_words else 'Paper'


def generate_output_for_all_papers(config_path: str = None):
    """
    모든 논문에 대해 본문 생성 및 output 폴더에 저장
    
    Args:
        config_path: 설정 파일 경로
    """
    if config_path is None:
        config_path = project_root / "config.yaml"
    
    # 설정 파일 로드
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(
            f"설정 파일을 찾을 수 없습니다: {config_path}\n"
            f"config.yaml.example을 참고하여 config.yaml을 생성해주세요."
        )
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 출력 폴더 생성
    output_dir = project_root / 'output'
    output_dir.mkdir(exist_ok=True)
    logger.info(f"출력 폴더: {output_dir}")
    
    # PaperManager 초기화
    paper_manager = PaperManager(
        papers_file=str(project_root / "data/papers.json"),
        state_file=str(project_root / "data/paper_state.json"),
        reset_on_first_run=False  # 상태 변경하지 않음
    )
    
    # 모든 논문 가져오기
    all_papers = paper_manager.papers
    
    if not all_papers:
        logger.error("논문 리스트가 비어있습니다.")
        return
    
    logger.info(f"총 {len(all_papers)}개의 논문에 대해 본문 생성 시작")
    
    # Claude 클라이언트 초기화 (API 키가 있는 경우)
    claude_client = None
    if 'claude' in config and config['claude'].get('api_key'):
        prompts_file = config.get('prompts_file', 'prompts.yaml')
        prompts_path = project_root / prompts_file
        claude_client = ClaudeClient(
            api_key=config['claude']['api_key'],
            model=config['claude'].get('model', 'claude-sonnet-4-20250514'),
            prompts_file=str(prompts_path)
        )
        logger.info("Claude 클라이언트 초기화 완료")
    else:
        logger.warning("Claude API 키가 없어 템플릿을 사용합니다.")
    
    # 이미지 찾기 클라이언트 초기화 (선택)
    image_finder = None
    image_config = config.get('image_search', {})
    google_api_key = image_config.get('google_api_key')
    google_cx = image_config.get('google_cx')
    if google_api_key and google_cx:
        image_finder = ImageFinder(google_api_key=google_api_key, google_cx=google_cx)
        logger.info("이미지 검색 클라이언트 초기화 완료")
    else:
        image_finder = ImageFinder()
        logger.info("기본 이미지 찾기 사용 (arXiv 등)")
    
    # 리뷰 모델 설정
    review_model = config.get('claude', {}).get('review_model')
    
    # 통계 변수
    success_count = 0
    error_count = 0
    
    # 모든 논문 처리
    for idx, paper in enumerate(all_papers, 1):
        try:
            paper_title = paper.get('title', '논문 리뷰')
            paper_year = paper.get('year', 'N/A')
            
            logger.info(f"[{idx}/{len(all_papers)}] 처리 중: {paper_title} ({paper_year}년)")
            
            # 약어 추출
            abbreviation = extract_abbreviation(paper_title)
            
            # 콘텐츠 생성
            content = generate_paper_review_content(
                paper=paper,
                claude_client=claude_client,
                review_number=idx,
                review_model=review_model
            )
            
            # 이미지 찾기 및 삽입
            if image_finder:
                try:
                    logger.info(f"  → 이미지 검색 중...")
                    images = image_finder.find_images_for_paper(
                        paper,
                        min_images=1,
                        max_images=5
                    )
                    if images:
                        arch_count = sum(1 for img in images if img.get('type') == 'architecture')
                        exp_count = sum(1 for img in images if img.get('type') == 'experiment')
                        int_count = sum(1 for img in images if img.get('type') == 'intuitive')
                        logger.info(f"  → {len(images)}개 이미지 찾음 (아키텍처: {arch_count}, 실험결과: {exp_count}, 기타: {int_count})")
                        content = insert_images_to_content(content, images, paper_title)
                    else:
                        logger.info(f"  → 이미지를 찾지 못함")
                except Exception as e:
                    logger.warning(f"  → 이미지 검색 중 오류 발생 (계속 진행): {e}")
            
            # 논문 메타정보 추가
            authors = paper.get('authors', [])
            authors_display = ', '.join(authors[:3]) if isinstance(authors, list) else str(authors)
            if isinstance(authors, list) and len(authors) > 3:
                authors_display += f" 외 {len(authors) - 3}명"
            
            meta_info = f"""# [{abbreviation}] {paper_title}

**저자**: {authors_display}  
**발행년도**: {paper.get('year', 'N/A')}년  
**인용수**: {paper.get('citations', 'N/A')}회  
"""
            if paper.get('url'):
                meta_info += f"**논문 링크**: [{paper.get('url')}]({paper.get('url')})  \n"
            if paper.get('arxiv_id'):
                meta_info += f"**arXiv ID**: {paper.get('arxiv_id')}  \n"
            
            meta_info += "\n---\n\n"
            full_content = meta_info + content
            
            # 파일명 생성
            safe_filename = sanitize_filename(paper_title)
            filename = f"{idx:04d}_{safe_filename}.md"
            filepath = output_dir / filename
            
            # 파일 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            logger.info(f"  ✓ 저장 완료: {filename}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"  ✗ 처리 실패: {paper_title} - {e}", exc_info=True)
            error_count += 1
    
    # 최종 통계
    logger.info("=" * 60)
    logger.info(f"본문 생성 완료!")
    logger.info(f"  성공: {success_count}개")
    logger.info(f"  실패: {error_count}개")
    logger.info(f"  총계: {len(all_papers)}개")
    logger.info(f"출력 폴더: {output_dir}")
    logger.info("=" * 60)


def main():
    """메인 함수"""
    try:
        import argparse
        
        parser = argparse.ArgumentParser(description='모든 논문에 대해 본문 생성 및 output 폴더에 저장')
        parser.add_argument(
            '--config',
            type=str,
            default=None,
            help='설정 파일 경로 (기본값: 프로젝트 루트의 config.yaml)'
        )
        
        args = parser.parse_args()
        
        generate_output_for_all_papers(config_path=args.config)
        
    except KeyboardInterrupt:
        logger.info("프로그램을 종료합니다.")
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)


if __name__ == "__main__":
    main()

