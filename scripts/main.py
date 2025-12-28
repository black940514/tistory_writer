"""
티스토리 자동 포스팅 메인 스크립트
"""
import sys
import yaml
import logging
from pathlib import Path
from typing import List

# 프로젝트 루트 경로
project_root = Path(__file__).parent.parent

# src 모듈 import를 위한 경로 추가
sys.path.insert(0, str(project_root))

from src.api.tistory_api import TistoryAPI
from src.content.content_generator import generate_paper_review_content
from src.data.post_manager import PostManager
from src.client.openai_client import OpenAIClient
from src.data.paper_manager import PaperManager
from src.data.paper_collector import PaperCollector
from src.content.image_finder import ImageFinder, insert_images_to_content

# 로그 디렉토리 생성
log_dir = project_root / 'data'
log_dir.mkdir(exist_ok=True)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'tistory_poster.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 스케줄러 모듈 (선택적)
try:
    from src.utils.scheduler import RandomScheduler
    SCHEDULER_AVAILABLE = True
    logger.debug("스케줄러 모듈 로드 성공")
except (ImportError, Exception) as e:
    SCHEDULER_AVAILABLE = False
    logger.debug(f"스케줄러 모듈을 사용할 수 없습니다: {e}")


class TistoryAutoPoster:
    """
    티스토리 자동 포스터
    
    논문 리스트에서 순차적으로 논문을 선택하여
    OpenAI로 리뷰를 생성하고 티스토리에 자동으로 포스팅합니다.
    """
    
    def __init__(self, config_path: str = None):
        """
        자동 포스터 초기화
        
        Args:
            config_path: 설정 파일 경로 (기본값: 프로젝트 루트의 config.yaml)
        """
        if config_path is None:
            config_path = project_root / "config.yaml"
        self.config = self._load_config(str(config_path))
        tistory_config = self.config['tistory']
        
        # 쿠키 우선, 없으면 ID/PW 사용
        blog_id = tistory_config.get('blog_id')  # 블로그 ID (선택적)
        if 'cookies' in tistory_config and tistory_config['cookies']:
            self.api = TistoryAPI(
                blog_name=tistory_config['blog_name'],
                cookies=tistory_config['cookies'],
                blog_id=blog_id
            )
        else:
            self.api = TistoryAPI(
                user_id=tistory_config['user_id'],
                user_pw=tistory_config['user_pw'],
                blog_name=tistory_config['blog_name'],
                blog_id=blog_id
            )
        self.post_manager = PostManager(state_file=str(project_root / "data/post_state.json"))
        self.paper_manager = PaperManager(papers_file=str(project_root / "data/papers.json"))
        self.category_id = None
        
        # OpenAI 클라이언트 초기화 (API 키가 있는 경우)
        self.openai_client = None
        if 'openai' in self.config and self.config['openai'].get('api_key'):
            prompts_file = self.config.get('prompts_file', 'prompts.yaml')
            prompts_path = project_root / prompts_file
            self.openai_client = OpenAIClient(
                api_key=self.config['openai']['api_key'],
                model=self.config['openai'].get('model', 'gpt-4o-mini'),
                prompts_file=str(prompts_path)
            )
            logger.info("OpenAI 클라이언트 초기화 완료")
        
        # 이미지 찾기 클라이언트 초기화 (선택)
        self.image_finder = None
        image_config = self.config.get('image_search', {})
        google_api_key = image_config.get('google_api_key')
        google_cx = image_config.get('google_cx')
        if google_api_key and google_cx:
            self.image_finder = ImageFinder(google_api_key=google_api_key, google_cx=google_cx)
            logger.info("이미지 검색 클라이언트 초기화 완료")
        else:
            # API 키가 없어도 기본 이미지 찾기 시도 (arXiv 등)
            self.image_finder = ImageFinder()
            logger.info("기본 이미지 찾기 사용 (arXiv 등)")
        
        self._init_category()
    
    def _load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(
                f"설정 파일을 찾을 수 없습니다: {config_path}\n"
                f"config.yaml.example을 참고하여 config.yaml을 생성해주세요."
            )
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logger.debug(f"Config loaded: {list(config.keys())}")
            if 'category' in config:
                logger.debug(f"Category config: {config['category']}")
            return config
    
    def _init_category(self):
        """카테고리 ID 초기화"""
        category_config = self.config.get('category', {})
        logger.debug(f"카테고리 설정: {category_config}")
        category_name = category_config.get('name', 'PaperReview')
        
        # 설정 파일에 카테고리 ID가 직접 지정된 경우 사용
        category_id = category_config.get('id')
        logger.debug(f"카테고리 ID (raw): {category_id}, type: {type(category_id)}")
        
        if category_id:
            self.category_id = str(category_id).strip()
            logger.info(f"카테고리 ID (설정 파일에서): {self.category_id} ({category_name})")
        else:
            # 카테고리 이름으로 조회
            logger.info(f"카테고리 ID가 설정되지 않음. 이름으로 조회 시도: {category_name}")
            self.category_id = self.api.get_category_id_by_name(category_name)
            
            if self.category_id is None or self.category_id == "0":
                logger.warning(
                    f"카테고리 '{category_name}'를 찾을 수 없습니다. "
                    f"미분류(0)로 게시됩니다."
                )
                self.category_id = "0"
            else:
                logger.info(f"카테고리 ID: {self.category_id} ({category_name})")
    
    def _extract_abbreviation(self, paper_title: str) -> str:
        """
        논문 제목에서 약어 추출 (개선된 로직)
        
        우선순위:
        1. 제목에 이미 [XXX] 형식이 있으면 추출
        2. 알려진 약어 사전 기반 키워드 매칭
        3. 제목의 주요 단어 첫 글자 조합으로 약어 생성 시도
        """
        import re
        
        # 1. 제목 앞에 [XXX] 형식이 있으면 추출
        bracket_match = re.match(r'\[([^\]]+)\]\s*(.+)', paper_title)
        if bracket_match:
            return bracket_match.group(1)
        
        title_lower = paper_title.lower()
        title_words = paper_title.split()
        
        # 2. 알려진 약어 사전 (키워드 → 약어 매핑)
        # 더 포괄적인 키워드 패턴 사용
        abbreviation_patterns = [
            # Vision & Transformer
            (['vision transformer', 'an image is worth', 'image is worth 16x16'], 'ViT'),
            (['swin transformer'], 'Swin'),
            (['transformer', 'attention is all you need'], 'Transformer'),
            (['convnext', 'convnet for the'], 'ConvNeXt'),
            
            # Self-Supervised Learning
            (['swav', 'swapping assignments', 'contrasting cluster assignments'], 'SwAV'),
            (['simclr', 'simple framework for contrastive', 'contrastive learning'], 'SimCLR'),
            (['moco', 'momentum contrast', 'contrast for unsupervised'], 'MoCo'),
            (['byol', 'bootstrap your own', 'self-supervised'], 'BYOL'),
            (['dino', 'knowledge distillation'], 'DINO'),
            (['mae', 'masked autoencoder'], 'MAE'),
            (['beit', 'bert pre-training'], 'BEiT'),
            (['dall-e', 'dalle'], 'DALL-E'),
            
            # Multimodal
            (['clip', 'natural language supervision', 'learning transferable'], 'CLIP'),
            (['blip', 'bootstrapping language-image'], 'BLIP'),
            (['flamingo', 'few-shot learning'], 'Flamingo'),
            (['llava', 'large language and vision'], 'LLaVA'),
            
            # Object Detection & Segmentation
            (['detr', 'end-to-end object detection'], 'DETR'),
            (['yolo'], 'YOLO'),
            (['mask r-cnn', 'mask rcnn'], 'Mask R-CNN'),
            (['faster r-cnn'], 'Faster R-CNN'),
            (['retinanet'], 'RetinaNet'),
            (['segment anything', 'sam'], 'SAM'),
            (['deeplab'], 'DeepLab'),
            
            # Generative Models
            (['diffusion'], 'DDPM'),  # 기본은 DDPM, 아래에서 더 구체적으로 확인
            (['latent diffusion', 'ldm'], 'LDM'),
            (['stable diffusion'], 'Stable Diffusion'),
            (['gan', 'generative adversarial'], 'GAN'),
            (['stylegan'], 'StyleGAN'),
            (['pix2pix'], 'Pix2Pix'),
            (['cyclegan'], 'CycleGAN'),
            (['progressive gan'], 'Progressive GAN'),
            
            # 3D & NeRF
            (['nerf', 'neural radiance fields'], 'NeRF'),
            (['instant ngp', 'instant neural graphics'], 'Instant-NGP'),
            (['gaussian splatting', '3d gaussian'], '3D-GS'),
            
            # Language Models
            (['gpt'], 'GPT'),
            (['bert', 'bidirectional encoder'], 'BERT'),
            (['t5', 'text-to-text transfer'], 'T5'),
            (['llama'], 'LLaMA'),
            (['sora'], 'Sora'),
            
            # Efficient & Compression
            (['lora', 'low-rank adaptation'], 'LoRA'),
            (['quantization'], 'Quantization'),
            (['knowledge distillation'], 'KD'),
            (['pruning'], 'Pruning'),
            
            # Video
            (['video transformer'], 'ViViT'),
            (['timesformer'], 'TimeSformer'),
            (['videomae'], 'VideoMAE'),
            
            # Others
            (['resnet', 'residual learning'], 'ResNet'),
            (['efficientnet'], 'EfficientNet'),
            (['mobilenet'], 'MobileNet'),
            (['regnet'], 'RegNet'),
            (['vision-language'], 'VLP'),
        ]
        
        # 키워드 패턴 매칭
        for keywords, abbrev in abbreviation_patterns:
            for keyword in keywords:
                if keyword in title_lower:
                    return abbrev
        
        # 3. 제목에서 약어 추출 시도 (단어의 첫 글자)
        # 주요 단어들 (불용어 제외)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        
        # 대문자로 시작하는 주요 단어 추출
        important_words = [w for w in title_words if w and w[0].isupper() and w.lower() not in stop_words]
        
        if len(important_words) >= 2:
            # 첫 3-4개 단어의 첫 글자로 약어 생성
            abbrev_candidates = []
            for word in important_words[:4]:
                # 단어가 이미 약어처럼 보이면 그대로 사용
                if len(word) <= 6 and word.isupper():
                    abbrev_candidates.append(word)
                else:
                    # 첫 글자만
                    abbrev_candidates.append(word[0].upper())
            
            # 약어 생성 (2-4글자)
            if abbrev_candidates:
                abbrev = ''.join(abbrev_candidates[:4])
                # 약어가 너무 길면 4글자로 제한
                if len(abbrev) > 4:
                    abbrev = abbrev[:4]
                # 최소 2글자는 되어야 함
                if len(abbrev) >= 2:
                    return abbrev
        
        # 4. 첫 단어가 이미 약어처럼 보이면 사용
        if title_words:
            first_word = title_words[0]
            # 대문자만 포함하고 2-6글자면 약어로 간주
            if first_word.isupper() and 2 <= len(first_word) <= 6:
                return first_word
            # 첫 글자들이 대문자이고 2-4글자면 약어로 간주 (예: "GPT-4", "BERT")
            caps_only = ''.join([c for c in first_word if c.isupper()])
            if len(caps_only) >= 2 and len(caps_only) <= 4:
                return caps_only
        
        # 5. 마지막 수단: 첫 단어 사용
        return title_words[0] if title_words else 'Paper'
        if 'segment anything' in title_lower or 'sam' in title_lower:
            return 'SAM'
        
        # YOLO 관련
        if 'yolo' in title_lower:
            return 'YOLO'
        
        # EfficientNet 관련
        if 'efficientnet' in title_lower:
            return 'EfficientNet'
        
        # BLIP 관련
        if 'blip' in title_lower:
            return 'BLIP'
        
        # GPT 관련
        if 'gpt' in title_lower:
            return 'GPT'
        
        # Sora 관련
        if 'sora' in title_lower:
            return 'Sora'
        
        # ConvNeXt 관련
        if 'convnext' in title_lower or 'convnet for the' in title_lower:
            return 'ConvNeXt'
        
        # 3. 없으면 제목의 첫 단어 사용 (대문자만)
        first_word = paper_title.split()[0] if paper_title.split() else 'Paper'
        # 대문자만 추출 (예: "DINOv2" -> "DINO")
        caps_only = ''.join([c for c in first_word if c.isupper()])
        if caps_only:
            return caps_only
        
        return first_word
    
    def create_post(self):
        """포스트 작성"""
        try:
            # 논문 리스트에서 다음 논문 가져오기
            paper = self.paper_manager.get_next_paper()
            
            if not paper:
                logger.error("리뷰할 논문이 없습니다. 논문 리스트를 먼저 생성해주세요.")
                raise Exception("논문 리스트가 비어있습니다.")
            
            # 제목 생성: [{약어}] 제목 전체
            paper_title = paper.get('title', '논문 리뷰')
            post_number = self.post_manager.get_next_post_number()
            abbreviation = self._extract_abbreviation(paper_title)
            title = f"[{abbreviation}] {paper_title}"
            
            logger.info(f"포스트 작성 시작: {title}")
            authors = paper.get('authors', [])
            authors_display = authors[:3] if isinstance(authors, list) else authors
            logger.info(f"논문 정보: {authors_display}, {paper.get('year', 'N/A')}년")
            
            # 콘텐츠 생성 (OpenAI 사용)
            review_model = self.config.get('openai', {}).get('review_model')
            content = generate_paper_review_content(
                paper=paper,
                openai_client=self.openai_client,
                review_number=post_number,
                review_model=review_model
            )
            
            # 이미지 찾기 및 삽입 (아키텍처 필수, 최대 5개)
            image_urls_to_embed = []
            if self.image_finder:
                try:
                    logger.info("논문 이미지 검색 중... (아키텍처, 실험결과, 직관적 이미지)")
                    images = self.image_finder.find_images_for_paper(
                        paper,
                        min_images=1,  # 최소 1개 (아키텍처 이미지)
                        max_images=5   # 최대 5개 (아키텍처 1-2개, 실험결과 1-2개, 직관적 1개)
                    )
                    if images:
                        arch_count = sum(1 for img in images if img.get('type') == 'architecture')
                        exp_count = sum(1 for img in images if img.get('type') == 'experiment')
                        int_count = sum(1 for img in images if img.get('type') == 'intuitive')
                        logger.info(f"총 {len(images)}개의 이미지를 찾았습니다. (아키텍처: {arch_count}, 실험결과: {exp_count}, 기타: {int_count})")
                        content = insert_images_to_content(content, images, paper_title)
                        # 이미지 URL 저장 (Base64 변환용)
                        image_urls_to_embed = [img.get('url', '') for img in images if img.get('url')]
                    else:
                        logger.warning("이미지를 찾지 못했습니다.")
                except Exception as e:
                    logger.warning(f"이미지 검색 중 오류 발생 (계속 진행): {e}")
            
            # 논문 메타정보 추가 (저자는 최대 3명만 표시)
            authors = paper.get('authors', [])
            authors_display = ', '.join(authors[:3]) if isinstance(authors, list) else str(authors)
            if isinstance(authors, list) and len(authors) > 3:
                authors_display += f" 외 {len(authors) - 3}명"
            
            meta_info = f"""# {paper_title}

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
            
            # HTML로 변환 (간단한 마크다운 → HTML)
            html_content = self._markdown_to_html(full_content, image_urls_to_embed)
            
            # 티스토리에 글 작성
            result = self.api.write_post(
                title=title,
                content=html_content,
                category_id=self.category_id
            )
            
            # 논문 리뷰 완료 표시
            self.paper_manager.mark_paper_reviewed(paper)
            
            logger.info(f"포스트 작성 완료: {title}")
            logger.info(f"포스트 URL: {result.get('url', 'N/A')}")
            
            # 진행 상황 상세 정보 로깅
            progress_info = self.paper_manager.get_progress_info()
            logger.info(f"진행 상황: {progress_info['reviewed_count']}/{progress_info['total_papers']} 논문 리뷰 완료 ({progress_info['progress_percent']}%)")
            logger.info(f"현재 인덱스: {progress_info['current_index']}, 남은 논문: {progress_info['remaining_count']}개")
            
            return result
            
        except Exception as e:
            logger.error(f"포스트 작성 실패: {e}", exc_info=True)
            raise
    
    def _markdown_to_html(self, markdown: str, image_urls: List[str] = None) -> str:
        """
        간단한 마크다운을 HTML로 변환
        
        Args:
            markdown: 마크다운 문자열
            image_urls: Base64로 변환할 이미지 URL 리스트
        """
        import re
        import base64
        import requests
        from typing import Optional
        from urllib.parse import urlparse, urlunparse
        
        if image_urls is None:
            image_urls = []
        
        def normalize_url(url: str) -> str:
            """URL 정규화 (프로토콜, www 등)"""
            if not url:
                return url
            # 이미 data URL이면 그대로 반환
            if url.startswith('data:'):
                return url
            # 프로토콜이 없으면 https 추가
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return url
        
        def download_image_to_base64(url: str, max_size_mb: float = 5.0) -> Optional[str]:
            """이미지 다운로드 및 Base64 변환 (재시도 포함)"""
            normalized_url = normalize_url(url)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/'
            }
            
            # 최대 3번 재시도
            for attempt in range(3):
                try:
                    response = requests.get(
                        normalized_url, 
                        timeout=15, 
                        headers=headers,
                        allow_redirects=True,
                        stream=True  # 스트리밍으로 받아서 크기 확인
                    )
                    
                    if response.status_code == 200:
                        # Content-Type 확인
                        content_type = response.headers.get('Content-Type', '').split(';')[0].strip()
                        
                        # 이미지가 아닌 경우도 시도 (일부 서버가 Content-Type을 잘못 설정)
                        # Content-Length 확인 (너무 큰 이미지는 제외)
                        content_length = response.headers.get('Content-Length')
                        if content_length:
                            size_mb = int(content_length) / (1024 * 1024)
                            if size_mb > max_size_mb:
                                logger.warning(f"이미지가 너무 큼 ({size_mb:.2f}MB > {max_size_mb}MB): {normalized_url[:60]}...")
                                # 스트리밍으로 받아서 처리
                                content = b''
                                for chunk in response.iter_content(chunk_size=8192):
                                    content += chunk
                                    if len(content) > max_size_mb * 1024 * 1024:
                                        logger.warning(f"이미지 크기 제한 초과, 중단: {normalized_url[:60]}...")
                                        return None
                            else:
                                content = response.content
                        else:
                            # Content-Length가 없으면 전체 받기 (하지만 크기 제한)
                            content = b''
                            for chunk in response.iter_content(chunk_size=8192):
                                content += chunk
                                if len(content) > max_size_mb * 1024 * 1024:
                                    logger.warning(f"이미지 크기 제한 초과: {normalized_url[:60]}...")
                                    return None
                        
                        if not content:
                            logger.warning(f"이미지 내용이 비어있음: {normalized_url[:60]}...")
                            return None
                        
                        # Content-Type이 없거나 이미지가 아니어도 시도
                        if not content_type or content_type not in ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']:
                            # Content-Type을 파일 확장자나 내용으로 추론
                            if normalized_url.lower().endswith(('.jpg', '.jpeg')):
                                content_type = 'image/jpeg'
                            elif normalized_url.lower().endswith('.png'):
                                content_type = 'image/png'
                            elif normalized_url.lower().endswith('.gif'):
                                content_type = 'image/gif'
                            elif normalized_url.lower().endswith('.webp'):
                                content_type = 'image/webp'
                            elif normalized_url.lower().endswith('.svg'):
                                content_type = 'image/svg+xml'
                            else:
                                # 파일 시그니처로 확인
                                if content.startswith(b'\xff\xd8\xff'):
                                    content_type = 'image/jpeg'
                                elif content.startswith(b'\x89PNG'):
                                    content_type = 'image/png'
                                elif content.startswith(b'GIF'):
                                    content_type = 'image/gif'
                                elif content.startswith(b'RIFF') and b'WEBP' in content[:20]:
                                    content_type = 'image/webp'
                                else:
                                    content_type = 'image/png'  # 기본값
                        
                        # Base64 인코딩
                        img_base64 = base64.b64encode(content).decode('utf-8')
                        data_url = f"data:{content_type};base64,{img_base64}"
                        
                        logger.info(f"이미지 Base64 변환 성공 ({len(content) / 1024:.1f}KB): {normalized_url[:60]}...")
                        return data_url
                    else:
                        logger.warning(f"이미지 다운로드 실패 (상태 코드: {response.status_code}): {normalized_url[:60]}...")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"이미지 다운로드 타임아웃 (시도 {attempt + 1}/3): {normalized_url[:60]}...")
                    if attempt < 2:
                        continue
                except requests.exceptions.RequestException as e:
                    logger.warning(f"이미지 다운로드 중 오류 (시도 {attempt + 1}/3): {e} - {normalized_url[:60]}...")
                    if attempt < 2:
                        continue
                except Exception as e:
                    logger.warning(f"이미지 처리 중 예외 (시도 {attempt + 1}/3): {e} - {normalized_url[:60]}...")
                    if attempt < 2:
                        continue
            
            return None
        
        # 이미지 URL을 Base64로 변환 (캐시)
        image_base64_cache = {}
        
        # 모든 이미지 URL을 Base64로 변환 시도
        for img_url in image_urls:
            if not img_url:
                continue
            
            # 이미 data URL이면 그대로 사용
            if img_url.startswith('data:'):
                image_base64_cache[img_url] = img_url
                continue
            
            # 캐시에 없으면 다운로드 시도
            if img_url not in image_base64_cache:
                base64_data = download_image_to_base64(img_url)
                if base64_data:
                    image_base64_cache[img_url] = base64_data
                    # 정규화된 URL도 캐시에 추가 (마크다운과 HTML에서 URL이 다를 수 있음)
                    normalized = normalize_url(img_url)
                    if normalized != img_url:
                        image_base64_cache[normalized] = base64_data
                else:
                    # 변환 실패 시에도 원본 URL 사용 (마지막 수단)
                    logger.warning(f"이미지 Base64 변환 실패, 원본 URL 사용: {img_url[:60]}...")
                    image_base64_cache[img_url] = normalize_url(img_url)
        
        lines = markdown.split('\n')
        result = []
        in_list = False
        list_type = None
        in_code = False
        code_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 코드 블록 처리
            if stripped.startswith('```'):
                if in_code:
                    # 코드 블록 종료
                    result.append(f"<pre><code>{'<br>'.join(code_lines)}</code></pre>")
                    code_lines = []
                    in_code = False
                else:
                    # 코드 블록 시작
                    in_code = True
                    if in_list:
                        result.append(f'</{list_type}>')
                        in_list = False
                i += 1
                continue
            
            if in_code:
                code_lines.append(line)
                i += 1
                continue
            
            # 제목 처리
            if stripped.startswith('### '):
                if in_list:
                    result.append(f'</{list_type}>')
                    in_list = False
                result.append(f'<h3>{stripped[4:]}</h3>')
                i += 1
                continue
            elif stripped.startswith('## '):
                if in_list:
                    result.append(f'</{list_type}>')
                    in_list = False
                result.append(f'<h2>{stripped[3:]}</h2>')
                i += 1
                continue
            elif stripped.startswith('# '):
                if in_list:
                    result.append(f'</{list_type}>')
                    in_list = False
                result.append(f'<h1>{stripped[2:]}</h1>')
                i += 1
                continue
            
            # 리스트 처리
            if stripped.startswith('- '):
                if not in_list or list_type != 'ul':
                    if in_list:
                        result.append(f'</{list_type}>')
                    result.append('<ul>')
                    in_list = True
                    list_type = 'ul'
                content = stripped[2:]
                # 강조 처리
                content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
                content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
                result.append(f'<li>{content}</li>')
            elif re.match(r'^\d+\.\s', stripped):
                if not in_list or list_type != 'ol':
                    if in_list:
                        result.append(f'</{list_type}>')
                    result.append('<ol>')
                    in_list = True
                    list_type = 'ol'
                content = re.sub(r'^\d+\.\s', '', stripped)
                # 강조 처리
                content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
                content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', content)
                result.append(f'<li>{content}</li>')
            else:
                if in_list:
                    result.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                
                if stripped:
                    # 이미지 처리 (![alt](url) 형식, 별도 줄)
                    img_match = re.match(r'^!\[([^\]]*)\]\(([^\)]+)\)\s*$', stripped)
                    if img_match:
                        alt_text = img_match.group(1)
                        img_url = img_match.group(2)
                        
                        # Base64로 변환된 이미지가 있으면 사용, 없으면 정규화된 URL 사용
                        img_src = image_base64_cache.get(img_url)
                        if not img_src:
                            # 정규화된 URL로도 시도
                            normalized_url = normalize_url(img_url)
                            img_src = image_base64_cache.get(normalized_url, normalized_url)
                        
                        # 이미지 태그 생성 (에러 처리 추가, Base64 또는 URL 모두 지원)
                        # Base64가 아니고 http(s)로 시작하지 않으면 정규화
                        if not img_src.startswith(('data:', 'http://', 'https://')):
                            img_src = normalize_url(img_src)
                        
                        img_tag = f'<p><img src="{img_src}" alt="{alt_text}" style="max-width: 100%; height: auto; display: block; margin: 0 auto;" onerror="this.style.display=\'none\';" /></p>'
                        result.append(img_tag)
                    else:
                        # 강조 처리
                        content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
                        content = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<em>\1</em>', content)
                        # 링크 처리
                        content = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', content)
                        result.append(f'<p>{content}</p>')
                else:
                    result.append('<br>')
            
            i += 1
        
        if in_list:
            result.append(f'</{list_type}>')
        if in_code:
            result.append(f"<pre><code>{'<br>'.join(code_lines)}</code></pre>")
        
        return '\n'.join(result)


def main():
    """메인 함수"""
    try:
        poster = TistoryAutoPoster()
        schedule_config = poster.config.get('schedule', {})
        scheduler_enabled = schedule_config.get('enabled', False)
        
        # 스케줄러 모드
        if scheduler_enabled and SCHEDULER_AVAILABLE:
            logger.info("=" * 60)
            logger.info("스케줄러 모드: 매일 자동으로 글을 작성합니다.")
            logger.info(f"실행 시간대: {schedule_config.get('start_hour', 18)}시 ~ {schedule_config.get('end_hour', 23)}시 {schedule_config.get('end_minute', 59)}분 사이 랜덤")
            logger.info("수동 실행을 원하면 config.yaml에서 schedule.enabled를 false로 변경하세요.")
            logger.info("=" * 60)
            scheduler = RandomScheduler(
                start_hour=schedule_config.get('start_hour', 18),
                end_hour=schedule_config.get('end_hour', 23),
                end_minute=schedule_config.get('end_minute', 59)
            )
            scheduler.schedule_daily_random(poster.create_post)
        elif scheduler_enabled and not SCHEDULER_AVAILABLE:
            logger.warning("스케줄러를 사용하려고 했지만 모듈을 찾을 수 없습니다. 즉시 실행 모드로 전환합니다.")
            logger.info("포스트 작성을 시작합니다...")
            poster.create_post()
            logger.info("포스트 작성이 완료되었습니다.")
        else:
            # 즉시 실행 모드 (기본값)
            logger.info("즉시 실행 모드: 포스트 작성을 시작합니다...")
            poster.create_post()
            logger.info("포스트 작성이 완료되었습니다.")
        
    except KeyboardInterrupt:
        logger.info("프로그램을 종료합니다.")
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)


if __name__ == "__main__":
    main()

