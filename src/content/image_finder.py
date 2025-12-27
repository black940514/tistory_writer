"""
논문 관련 이미지 찾기 모듈
"""
import logging
import requests
import re
import time
from typing import List, Optional, Dict, Set
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus, urljoin

logger = logging.getLogger(__name__)


class ImageFinder:
    """논문 아키텍처/구조 이미지 찾기"""
    
    def __init__(self, google_api_key: Optional[str] = None, google_cx: Optional[str] = None):
        """
        Args:
            google_api_key: Google Custom Search API 키 (선택)
            google_cx: Google Custom Search Engine ID (선택)
        """
        self.google_api_key = google_api_key
        self.google_cx = google_cx
    
    def find_images_for_paper(
        self,
        paper: Dict,
        min_images: int = 1,
        max_images: int = 3
    ) -> List[Dict]:
        """
        논문에 대한 아키텍처 이미지 찾기
        
        Args:
            paper: 논문 정보 (title, arxiv_id, url 등)
            min_images: 최소 이미지 개수 (기본값: 1)
            max_images: 최대 이미지 개수 (기본값: 3)
        
        Returns:
            이미지 정보 리스트 [{"url": "...", "title": "...", "source": "..."}]
        """
        images = []
        seen_urls: Set[str] = set()
        
        # 1. arXiv 논문에서 이미지 추출 시도 (최우선)
        if paper.get('arxiv_id'):
            arxiv_images = self._extract_arxiv_images(paper)
            for img in arxiv_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    if len(images) >= max_images:
                        return images[:max_images]
        
        # 2. Papers with Code에서 이미지 찾기
        if len(images) < min_images:
            pw_code_images = self._extract_paperswithcode_images(paper)
            for img in pw_code_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    if len(images) >= max_images:
                        return images[:max_images]
        
        # 3. Google Custom Search로 이미지 검색 (여러 쿼리 시도)
        if len(images) < min_images and self.google_api_key and self.google_cx:
            search_images = self._search_google_images_enhanced(paper, max_images - len(images))
            for img in search_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    if len(images) >= max_images:
                        return images[:max_images]
        
        # 4. 논문 URL에서 직접 이미지 추출
        if len(images) < min_images and paper.get('url'):
            direct_images = self._extract_direct_url_images(paper)
            for img in direct_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    if len(images) >= max_images:
                        return images[:max_images]
        
        # 5. Fallback: arXiv 페이지 추가 검색
        if len(images) < min_images:
            fallback_images = self._find_fallback_images(paper, max_images - len(images))
            for img in fallback_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    if len(images) >= max_images:
                        return images[:max_images]
        
        return images[:max_images]
    
    def _extract_arxiv_images(self, paper: Dict) -> List[Dict]:
        """arXiv 논문 페이지에서 이미지 추출 (개선)"""
        images = []
        arxiv_id = paper.get('arxiv_id')
        
        if not arxiv_id:
            return images
        
        try:
            # arXiv 페이지 URL
            url = f"https://arxiv.org/abs/{arxiv_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=15, headers=headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 1. Open Graph 이미지 (메타 태그)
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    img_url = og_image['content']
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif not img_url.startswith('http'):
                        img_url = urljoin('https://arxiv.org', img_url)
                    images.append({
                        'url': img_url,
                        'title': f"{paper.get('title', 'Paper')} - Preview",
                        'source': 'arXiv (OG Image)',
                        'type': 'architecture'
                    })
                
                # 2. arXiv PDF 첫 페이지 썸네일 (일반적인 패턴)
                arxiv_id_clean = arxiv_id.replace('arXiv:', '').strip()
                # arXiv는 보통 PDF의 첫 페이지를 썸네일로 제공
                thumbnail_urls = [
                    f"https://arxiv.org/pdf/{arxiv_id_clean}/page/1",
                    f"https://arxiv.org/html/{arxiv_id_clean}/thumb.jpg",
                ]
                for thumb_url in thumbnail_urls:
                    images.append({
                        'url': thumb_url,
                        'title': f"{paper.get('title', 'Paper')} - First Page",
                        'source': 'arXiv (PDF Thumbnail)',
                        'type': 'architecture'
                    })
                    break  # 하나만 추가
                
                # 3. arXiv abs 페이지의 이미지 태그 (더 포괄적으로)
                img_tags = soup.find_all('img')
                for img in img_tags:
                    src = img.get('src', '') or img.get('data-src', '')
                    if not src:
                        continue
                    
                    # arXiv 관련 이미지만
                    if 'arxiv' in src.lower():
                        full_url = src if src.startswith('http') else urljoin('https://arxiv.org', src)
                        # 썸네일이나 다이어그램 관련 이미지 우선
                        if any(keyword in src.lower() for keyword in ['thumb', 'figure', 'diagram', 'graph']):
                            images.append({
                                'url': full_url,
                                'title': f"{paper.get('title', 'Paper')} - Diagram",
                                'source': 'arXiv (Figure)',
                                'type': 'architecture'
                            })
                            if len(images) >= 3:  # 최대 3개
                                break
                
                # 4. 논문 제목에서 키워드 추출하여 arXiv 이미지 검색 시도
                # (이미 충분한 이미지를 찾았으면 스킵)
                
        except Exception as e:
            logger.warning(f"arXiv 이미지 추출 실패: {e}")
        
        return images
    
    def _search_google_images_enhanced(
        self,
        paper: Dict,
        max_results: int = 3,
        image_type: str = 'architecture'  # 'architecture', 'experiment', 'intuitive'
    ) -> List[Dict]:
        """Google Custom Search API로 이미지 검색 (개선: 이미지 유형별 검색)"""
        images = []
        
        if not self.google_api_key or not self.google_cx:
            return images
        
        title = paper.get('title', '')
        authors = paper.get('authors', [])
        first_author = authors[0] if isinstance(authors, list) and len(authors) > 0 else ''
        
        # 이미지 유형별 검색 쿼리 생성
        queries = []
        
        if image_type == 'architecture':
            # 아키텍처 이미지 검색 쿼리
            queries.append(f"{title} architecture diagram")
            queries.append(f"{title} model architecture")
            queries.append(f"{title} network diagram")
            queries.append(f"{title} system architecture")
            queries.append(f"{title} framework diagram")
        elif image_type == 'experiment':
            # 실험 결과 이미지 검색 쿼리
            queries.append(f"{title} experimental results")
            queries.append(f"{title} performance comparison")
            queries.append(f"{title} results graph")
            queries.append(f"{title} evaluation results")
            queries.append(f"{title} benchmark results")
        else:  # intuitive
            # 직관적 이미지 검색 쿼리
            queries.append(f"{title} visualization")
            queries.append(f"{title} overview")
            queries.append(f"{title} illustration")
            queries.append(f"{title} concept")
        
        # 제목에서 주요 키워드 추출하여 쿼리 추가
        if title:
            # 괄호 안의 내용 (약어 등) 추출
            abbrev_match = re.search(r'\(([A-Za-z0-9\-\s]+)\)', title)
            if abbrev_match:
                abbrev = abbrev_match.group(1)
                if image_type == 'architecture':
                    queries.append(f"{abbrev} architecture diagram")
                    queries.append(f"{abbrev} model")
                elif image_type == 'experiment':
                    queries.append(f"{abbrev} results")
                    queries.append(f"{abbrev} performance")
            
            # 대문자로 시작하는 주요 단어 추출
            keywords = re.findall(r'\b[A-Z][a-z]+', title)
            if keywords:
                main_keywords = ' '.join(keywords[:3])  # 처음 3개 키워드
                if image_type == 'architecture':
                    queries.append(f"{main_keywords} architecture")
                elif image_type == 'experiment':
                    queries.append(f"{main_keywords} results")
        
        # 저자 + 제목 조합
        if first_author and len(title) < 100:  # 제목이 너무 길면 생략
            if image_type == 'architecture':
                queries.append(f"{first_author} {title} architecture")
            elif image_type == 'experiment':
                queries.append(f"{first_author} {title} results")
        
        # 각 쿼리로 검색 시도 (최대 max_results까지)
        seen_urls = set()
        for query in queries[:5]:  # 최대 5개 쿼리 시도
            if len(images) >= max_results:
                break
            
            try:
                search_url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cx,
                    'q': query,
                    'searchType': 'image',
                    'num': min(5, max_results - len(images)),  # 한 번에 최대 5개
                    'safe': 'active',
                    'imgSize': 'large',
                    'fileType': 'jpg,png',  # 일반적인 이미지 형식
                }
                
                response = requests.get(search_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    
                    for item in items:
                        img_url = item.get('link', '')
                        if img_url and img_url not in seen_urls:
                            seen_urls.add(img_url)
                            image_title = item.get('title', '')
                            if image_type == 'architecture':
                                title_suffix = 'Architecture Diagram'
                            elif image_type == 'experiment':
                                title_suffix = 'Experimental Results'
                            else:
                                title_suffix = 'Visualization'
                            
                            images.append({
                                'url': img_url,
                                'title': image_title or f"{title} - {title_suffix}",
                                'source': f'Google Image Search ({query[:30]}...)',
                                'type': image_type
                            })
                            if len(images) >= max_results:
                                break
                
                # API 제한을 고려한 짧은 지연
                time.sleep(0.3)
                
            except Exception as e:
                logger.debug(f"Google 이미지 검색 쿼리 실패 ({query[:30]}...): {e}")
                continue
        
        return images
    
    def _extract_paperswithcode_images(self, paper: Dict) -> List[Dict]:
        """Papers with Code에서 이미지 추출"""
        images = []
        title = paper.get('title', '')
        
        if not title:
            return images
        
        try:
            # Papers with Code 검색 URL
            search_query = quote_plus(title[:100])  # 제목의 처음 100자만
            search_url = f"https://paperswithcode.com/search?q={search_query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(search_url, timeout=15, headers=headers, allow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Papers with Code의 논문 카드에서 이미지 찾기
                # 일반적으로 논문 카드에는 썸네일이나 다이어그램이 있음
                paper_cards = soup.find_all('div', class_=re.compile(r'paper-card|entity', re.I))
                
                for card in paper_cards[:3]:  # 최대 3개 카드 확인
                    # 이미지 태그 찾기
                    img_tags = card.find_all('img')
                    for img in img_tags:
                        src = img.get('src', '') or img.get('data-src', '')
                        if src and 'paper' in src.lower():
                            full_url = src if src.startswith('http') else urljoin('https://paperswithcode.com', src)
                            images.append({
                                'url': full_url,
                                'title': f"{title} - Papers with Code",
                                'source': 'Papers with Code',
                                'type': 'architecture'
                            })
                            break
                    if len(images) >= 2:
                        break
        
        except Exception as e:
            logger.debug(f"Papers with Code 이미지 추출 실패: {e}")
        
        return images
    
    def _extract_direct_url_images(self, paper: Dict) -> List[Dict]:
        """논문 URL에서 직접 이미지 추출"""
        images = []
        paper_url = paper.get('url', '')
        
        if not paper_url:
            return images
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(paper_url, timeout=15, headers=headers, allow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Open Graph 이미지
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    img_url = og_image['content']
                    if not img_url.startswith('http'):
                        img_url = urljoin(paper_url, img_url)
                    images.append({
                        'url': img_url,
                        'title': f"{paper.get('title', 'Paper')} - Preview",
                        'source': 'Paper URL (OG Image)',
                        'type': 'intuitive'
                    })
                
                # 주요 이미지 태그 찾기 (figure, diagram 관련)
                img_tags = soup.find_all('img')
                for img in img_tags[:10]:  # 처음 10개만 확인
                    src = img.get('src', '') or img.get('data-src', '')
                    if not src:
                        continue
                    
                    # 다이어그램이나 아키텍처 관련 키워드가 있는 이미지
                    alt_text = img.get('alt', '').lower()
                    if any(keyword in alt_text for keyword in ['architecture', 'diagram', 'figure', 'model', 'network']):
                        full_url = src if src.startswith('http') else urljoin(paper_url, src)
                        images.append({
                            'url': full_url,
                            'title': alt_text or f"{paper.get('title', 'Paper')} - Diagram",
                            'source': 'Paper URL',
                            'type': 'architecture' if any(k in alt_text for k in ['architecture', 'diagram', 'model', 'network']) else 'intuitive'
                        })
                        if len(images) >= 2:
                            break
        
        except Exception as e:
            logger.debug(f"직접 URL 이미지 추출 실패: {e}")
        
        return images
    
    def _validate_image_url(self, url: str) -> bool:
        """이미지 URL 유효성 검증"""
        if not url or len(url) < 10:
            return False
        
        # 유효한 URL 형식인지 확인
        try:
            parsed = urlparse(url)
            if not parsed.scheme or parsed.scheme not in ['http', 'https']:
                return False
            if not parsed.netloc:
                return False
        except Exception:
            return False
        
        # 이미지 확장자 확인 (선택적, 많은 이미지가 쿼리 파라미터로 제공됨)
        # img_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        # if not any(ext in url.lower() for ext in img_extensions) and '.' not in url.split('/')[-1]:
        #     # 확장자가 없어도 URL 형식이면 통과 (동적 이미지)
        #     pass
        
        return True
    
    def _find_fallback_images(
        self,
        paper: Dict,
        max_results: int = 2
    ) -> List[Dict]:
        """Fallback 이미지 찾기 (arXiv 추가 검색)"""
        images = []
        
        try:
            # arXiv 논문 페이지에서 추가 이미지 찾기 (이미 시도했을 수 있지만 다시 확인)
            arxiv_id = paper.get('arxiv_id')
            title = paper.get('title', '')
            
            if arxiv_id:
                # arXiv PDF 링크에서 직접 썸네일 생성 URL 시도
                arxiv_id_clean = arxiv_id.replace('arXiv:', '').strip()
                # arXiv는 보통 특정 패턴으로 썸네일을 제공하지 않지만, PDF 링크는 제공
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id_clean}"
                # PDF 링크 자체는 이미지가 아니므로 스킵
                
                # 대신 abs 페이지를 다시 확인 (메타 태그 등)
                url = f"https://arxiv.org/abs/{arxiv_id_clean}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, timeout=10, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 메타 태그에서 썸네일 찾기
                    meta_image = soup.find('meta', property='og:image')
                    if meta_image and meta_image.get('content'):
                        img_url = meta_image['content']
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        elif not img_url.startswith('http'):
                            img_url = urljoin('https://arxiv.org', img_url)
                        images.append({
                            'url': img_url,
                            'title': f"{title} - Paper Preview",
                            'source': 'arXiv (Fallback)',
                            'type': 'architecture'
                        })
            
        except Exception as e:
            logger.debug(f"Fallback 이미지 찾기 실패: {e}")
        
        return images


def insert_images_to_content(content: str, images: List[Dict], paper_title: str) -> str:
    """
    생성된 콘텐츠에 이미지 삽입
    
    Args:
        content: 마크다운 콘텐츠
        images: 이미지 정보 리스트
        paper_title: 논문 제목
    
    Returns:
        이미지가 삽입된 마크다운 콘텐츠
    """
    if not images:
        return content
    
    # 이미지 마크다운 형식 생성
    image_blocks = []
    for i, img in enumerate(images, 1):
        title = img.get('title', f'아키텍처 다이어그램 {i}')
        url = img.get('url', '')
        if url:
            image_block_lines = [f"![{title}]({url})"]
            if img.get('source'):
                image_block_lines.append(f"*출처: {img['source']}*")
            image_blocks.append(image_block_lines)
    
    if not image_blocks:
        return content
    
    # 섹션별 삽입 위치 정의
    lines = content.split('\n')
    inserted_count = 0
    
    # 첫 번째 이미지: "방법", "해결", "아키텍처", "구조" 관련 섹션 뒤
    for i, line in enumerate(lines):
        if inserted_count < len(image_blocks) and line.startswith('##') and not line.startswith('###'):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in ['방법', '해결', '아키텍처', '구조', 'method', 'approach']):
                # 해당 섹션 다음 8줄 뒤에 삽입
                insert_pos = min(i + 8, len(lines))
                for img_line in reversed(image_blocks[inserted_count]):
                    lines.insert(insert_pos, img_line)
                inserted_count += 1
                break
    
    # 두 번째 이미지: "실험", "결과" 관련 섹션 뒤 (있을 경우)
    if inserted_count < len(image_blocks):
        for i, line in enumerate(lines):
            if inserted_count < len(image_blocks) and line.startswith('##') and not line.startswith('###'):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['실험', '결과', 'experiment', 'result']):
                    insert_pos = min(i + 8, len(lines))
                    for img_line in reversed(image_blocks[inserted_count]):
                        lines.insert(insert_pos, img_line)
                    inserted_count += 1
                    break
    
    # 세 번째 이미지: 첫 번째 주요 섹션 뒤 (있을 경우)
    if inserted_count < len(image_blocks):
        for i, line in enumerate(lines):
            if line.startswith('##') and not line.startswith('###') and i > 5:
                insert_pos = min(i + 8, len(lines))
                for img_line in reversed(image_blocks[inserted_count]):
                    lines.insert(insert_pos, img_line)
                inserted_count += 1
                break
    
    # 이미지가 하나도 삽입되지 않았으면 첫 번째 ## 섹션 뒤에 추가
    if inserted_count == 0 and image_blocks:
        for i, line in enumerate(lines):
            if line.startswith('##') and not line.startswith('###'):
                insert_pos = min(i + 8, len(lines))
                for img_line in reversed(image_blocks[0]):
                    lines.insert(insert_pos, img_line)
                break
    
    return '\n'.join(lines)

