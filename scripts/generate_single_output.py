"""
단일 논문 제목 또는 arXiv 링크를 입력받아 본문 생성 및 output 폴더에 저장
"""
import sys
import yaml
import logging
import re
import requests
import argparse
from pathlib import Path
from typing import Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# 프로젝트 루트 경로
from scripts.get_project_root import get_project_root
project_root = get_project_root()

# src 모듈 import를 위한 경로 추가
sys.path.insert(0, str(project_root))

from src.content.content_generator import generate_paper_review_content
from src.client.claude_client import ClaudeClient
from src.content.image_finder import ImageFinder, insert_images_to_content

# 로그 디렉토리 생성
log_dir = project_root / 'data'
log_dir.mkdir(exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'single_output_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def extract_arxiv_id(url_or_id: str) -> Optional[str]:
    """
    arXiv URL 또는 ID에서 arXiv ID 추출
    
    Args:
        url_or_id: arXiv URL 또는 ID (예: https://arxiv.org/abs/2301.00001, 2301.00001)
    
    Returns:
        arXiv ID (예: 2301.00001) 또는 None
    """
    # 이미 순수 ID인 경우
    if re.match(r'^\d{4}\.\d{5}(v\d+)?$', url_or_id):
        return url_or_id
    
    # URL에서 추출
    patterns = [
        r'arxiv\.org/abs/([0-9]+\.[0-9]+(v\d+)?)',
        r'arxiv\.org/pdf/([0-9]+\.[0-9]+(v\d+)?)',
        r'arxiv\.org/html/([0-9]+\.[0-9]+(v\d+)?)',
        r'([0-9]{4}\.[0-9]{5}(v\d+)?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def fetch_arxiv_paper_info(arxiv_id: str) -> Optional[Dict]:
    """
    arXiv API를 사용하여 논문 정보 가져오기
    
    Args:
        arxiv_id: arXiv ID (예: 2301.00001)
    
    Returns:
        논문 정보 딕셔너리 또는 None
    """
    try:
        # arXiv API v1 사용
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, timeout=15, headers=headers)
        if response.status_code != 200:
            logger.warning(f"arXiv API 요청 실패: HTTP {response.status_code}")
            return None
        
        # XML 파싱
        soup = BeautifulSoup(response.text, 'xml')
        entry = soup.find('entry')
        
        if not entry:
            logger.warning("arXiv API 응답에 entry가 없습니다")
            return None
        
        # 제목 추출
        title_elem = entry.find('title')
        title = title_elem.text.strip().replace('\n', ' ') if title_elem else "Unknown Title"
        
        # 저자 추출
        authors = []
        for author in entry.find_all('author'):
            name_elem = author.find('name')
            if name_elem:
                authors.append(name_elem.text.strip())
        
        # 발행년도 추출
        published_elem = entry.find('published')
        year = None
        if published_elem:
            try:
                year = int(published_elem.text[:4])
            except:
                pass
        
        # 초록 추출
        summary_elem = entry.find('summary')
        abstract = summary_elem.text.strip().replace('\n', ' ') if summary_elem else None
        
        # URL
        id_elem = entry.find('id')
        url = id_elem.text.strip() if id_elem else f"https://arxiv.org/abs/{arxiv_id}"
        
        # arXiv ID 정리 (버전 제거)
        arxiv_id_clean = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
        
        paper_info = {
            'title': title,
            'authors': authors,
            'year': year,
            'citations': None,  # arXiv API에는 인용수가 없음
            'importance_score': None,
            'url': url,
            'arxiv_id': arxiv_id_clean,
            'abstract': abstract
        }
        
        logger.info(f"arXiv에서 논문 정보 추출 성공: {title}")
        return paper_info
        
    except Exception as e:
        logger.error(f"arXiv API 호출 실패: {e}", exc_info=True)
        return None


def extract_abbreviation(paper_title: str) -> str:
    """
    논문 제목에서 약어 추출
    """
    # 1. 제목 앞에 [XXX] 형식이 있으면 추출
    bracket_match = re.match(r'\[([^\]]+)\]\s*(.+)', paper_title)
    if bracket_match:
        return bracket_match.group(1)
    
    title_lower = paper_title.lower()
    title_words = paper_title.split()
    
    # 2. 알려진 약어 사전
    abbreviation_patterns = [
        (['vision transformer', 'an image is worth'], 'ViT'),
        (['swin transformer'], 'Swin'),
        (['transformer', 'attention is all you need'], 'Transformer'),
        (['convnext'], 'ConvNeXt'),
        (['swav'], 'SwAV'),
        (['simclr'], 'SimCLR'),
        (['moco', 'momentum contrast'], 'MoCo'),
        (['byol'], 'BYOL'),
        (['dino'], 'DINO'),
        (['mae', 'masked autoencoder'], 'MAE'),
        (['beit'], 'BEiT'),
        (['clip'], 'CLIP'),
        (['blip'], 'BLIP'),
        (['detr'], 'DETR'),
        (['yolo'], 'YOLO'),
        (['mask r-cnn'], 'Mask R-CNN'),
        (['segment anything', 'sam'], 'SAM'),
        (['diffusion'], 'DDPM'),
        (['latent diffusion'], 'LDM'),
        (['stable diffusion'], 'Stable Diffusion'),
        (['gan'], 'GAN'),
        (['nerf'], 'NeRF'),
        (['gpt'], 'GPT'),
        (['bert'], 'BERT'),
        (['llama'], 'LLaMA'),
        (['sora'], 'Sora'),
        (['resnet'], 'ResNet'),
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
    
    return title_words[0] if title_words else 'Paper'


def sanitize_filename(title: str, max_length: int = 100) -> str:
    """
    논문 제목을 안전한 파일명으로 변환
    """
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    filename = filename.strip('_')
    
    if not filename:
        filename = "paper"
    
    return filename


def generate_paper_info_from_title(title: str, claude_client: Optional[ClaudeClient] = None) -> Dict:
    """
    논문 제목으로부터 논문 정보 생성 (Claude 사용 또는 기본값)

    Args:
        title: 논문 제목
        claude_client: Claude 클라이언트 (선택)

    Returns:
        논문 정보 딕셔너리
    """
    # 기본값 (제목은 항상 설정)
    default_paper = {
        'title': title,
        'authors': [],
        'year': None,
        'citations': None,
        'importance_score': None,
        'url': None,
        'arxiv_id': None,
        'abstract': None
    }

    if claude_client:
        try:
            # Claude로 논문 정보 생성 시도
            papers = claude_client.generate_paper_details([title])
            if papers and len(papers) > 0:
                paper = papers[0]
                # 제목이 없으면 기본 제목 사용
                if not paper.get('title'):
                    paper['title'] = title
                logger.info(f"Claude로 논문 정보 생성 성공: {paper.get('title', title)}")
                return paper
            else:
                logger.warning("Claude 응답이 비어있습니다. 기본값 사용")
        except Exception as e:
            logger.warning(f"Claude로 논문 정보 생성 실패, 기본값 사용: {e}")
    
    logger.info(f"기본값으로 논문 정보 생성: {title}")
    return default_paper


def generate_single_output(
    input_str: str,
    config_path: str = None,
    output_filename: str = None,
    output_dir_override: str = None
) -> Optional[str]:
    """
    단일 논문에 대해 본문 생성 및 저장

    Args:
        input_str: 논문 제목 또는 arXiv URL
        config_path: 설정 파일 경로
        output_filename: 출력 파일명 (None이면 자동 생성)
        output_dir_override: 출력 폴더 경로 (None이면 기본값 사용)

    Returns:
        생성된 파일 경로 또는 None
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
    if output_dir_override:
        output_dir = Path(output_dir_override) / 'output'
    else:
        output_dir = project_root / 'output'
    output_dir.mkdir(exist_ok=True)
    logger.info(f"출력 폴더: {output_dir}")
    
    # 논문 정보 추출
    paper = None
    
    # 1. arXiv URL/ID인지 확인
    arxiv_id = extract_arxiv_id(input_str)
    if arxiv_id:
        logger.info(f"arXiv ID 감지: {arxiv_id}")
        paper = fetch_arxiv_paper_info(arxiv_id)
        if not paper:
            logger.warning("arXiv에서 정보를 가져오지 못했습니다. 제목으로 처리합니다.")
            paper = generate_paper_info_from_title(input_str)
    else:
        # 2. 논문 제목으로 처리
        logger.info(f"논문 제목으로 처리: {input_str}")
        paper = generate_paper_info_from_title(input_str)
    
    if not paper:
        logger.error("논문 정보를 생성할 수 없습니다.")
        return None
    
    # Claude 클라이언트 초기화
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
    
    # 이미지 찾기 클라이언트 초기화
    image_finder = None
    image_config = config.get('image_search', {})
    google_api_key = image_config.get('google_api_key')
    google_cx = image_config.get('google_cx')
    if google_api_key and google_cx:
        image_finder = ImageFinder(google_api_key=google_api_key, google_cx=google_cx, output_dir=str(output_dir))
        logger.info("이미지 검색 클라이언트 초기화 완료")
    else:
        image_finder = ImageFinder(output_dir=str(output_dir))
        logger.info("기본 이미지 찾기 사용 (arXiv 등)")
    
    # 리뷰 모델 설정
    review_model = config.get('claude', {}).get('review_model')

    # 논문 제목
    paper_title = paper.get('title', input_str)
    logger.info(f"논문 처리 시작: {paper_title}")

    # 약어 추출
    abbreviation = extract_abbreviation(paper_title)

    # 콘텐츠 생성
    logger.info("본문 생성 중...")
    content = generate_paper_review_content(
        paper=paper,
        claude_client=claude_client,
        review_number=None,
        review_model=review_model
    )
    
    # 이미지 찾기 및 삽입
    if image_finder:
        try:
            logger.info("이미지 검색 중...")
            images = image_finder.find_images_for_paper(
                paper,
                min_images=1,
                max_images=5
            )
            if images:
                arch_count = sum(1 for img in images if img.get('type') == 'architecture')
                exp_count = sum(1 for img in images if img.get('type') == 'experiment')
                int_count = sum(1 for img in images if img.get('type') == 'intuitive')
                logger.info(f"{len(images)}개 이미지 찾음 (아키텍처: {arch_count}, 실험결과: {exp_count}, 기타: {int_count})")
                content = insert_images_to_content(content, images, paper_title)
            else:
                logger.info("이미지를 찾지 못함")
        except Exception as e:
            logger.warning(f"이미지 검색 중 오류 발생 (계속 진행): {e}")
    
    # 논문 메타정보 추가
    authors = paper.get('authors', [])
    authors_display = ', '.join(authors[:3]) if isinstance(authors, list) and authors else "N/A"
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
    if output_filename:
        filename = output_filename
        if not filename.endswith('.md'):
            filename += '.md'
    else:
        safe_filename = sanitize_filename(paper_title)
        filename = f"{safe_filename}.md"
    
    filepath = output_dir / filename
    
    # 파일 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    logger.info(f"✓ 저장 완료: {filepath}")
    return str(filepath)


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='단일 논문 제목 또는 arXiv 링크를 입력받아 본문 생성 및 output 폴더에 저장'
    )
    parser.add_argument(
        'input',
        type=str,
        help='논문 제목 또는 arXiv URL (예: "Attention Is All You Need" 또는 "https://arxiv.org/abs/1706.03762")'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='설정 파일 경로 (기본값: 프로젝트 루트의 config.yaml)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='출력 파일명 (기본값: 논문 제목 기반 자동 생성)'
    )
    
    args = parser.parse_args()
    
    try:
        filepath = generate_single_output(
            input_str=args.input,
            config_path=args.config,
            output_filename=args.output
        )
        
        if filepath:
            print(f"\n✓ 본문 생성 완료: {filepath}")
        else:
            print("\n✗ 본문 생성 실패")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("프로그램을 종료합니다.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

