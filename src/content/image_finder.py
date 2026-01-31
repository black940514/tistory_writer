"""
논문 관련 이미지 찾기 모듈 (개선 버전)
- arXiv HTML(ar5iv) Figure 추출
- PDF 다운로드 후 이미지 추출
- 구글 이미지 검색
"""
import logging
import requests
import re
import time
import os
import tempfile
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Set
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus, urljoin

logger = logging.getLogger(__name__)

# PDF 이미지 추출을 위한 pymupdf (선택적)
try:
    import fitz  # pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.debug("pymupdf not available - PDF image extraction disabled")


class ImageFinder:
    """논문 아키텍처/구조 이미지 찾기 (개선 버전)"""

    def __init__(self, google_api_key: Optional[str] = None, google_cx: Optional[str] = None, output_dir: Optional[str] = None):
        """
        Args:
            google_api_key: Google Custom Search API 키 (선택)
            google_cx: Google Custom Search Engine ID (선택)
            output_dir: 이미지 저장 디렉토리 (기본값: output/images)
        """
        self.google_api_key = google_api_key
        self.google_cx = google_cx

        # 이미지 저장 디렉토리 설정
        if output_dir:
            self.IMAGE_DIR = Path(output_dir) / "images"
        else:
            self.IMAGE_DIR = Path("output") / "images"
        self.IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _search_arxiv_by_title(self, title: str) -> Optional[str]:
        """논문 제목으로 arXiv에서 arxiv_id 검색"""
        try:
            # 제목에서 핵심 키워드 추출 (짧은 단어, 불용어 제외)
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                         'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                         'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                         'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                         'from', 'as', 'into', 'through', 'during', 'before', 'after',
                         'above', 'below', 'between', 'under', 'again', 'further', 'then',
                         'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
                         'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
                         'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
                         'and', 'but', 'if', 'or', 'because', 'until', 'while', 'although',
                         'you', 'your', 'yours', 'yourself', 'yourselves', 'we', 'our', 'ours'}

            words = re.findall(r'\b[A-Za-z]+\b', title)
            keywords = [w for w in words if w.lower() not in stop_words and len(w) > 2][:5]

            # 여러 검색 쿼리 시도
            queries = [
                f'ti:"{title}"',  # 정확한 제목
                f'all:{"+".join(keywords)}',  # 키워드 조합
            ]

            headers = {'User-Agent': 'Mozilla/5.0'}

            for query in queries:
                search_query = quote_plus(query)
                url = f"http://export.arxiv.org/api/query?search_query={search_query}&start=0&max_results=5"

                response = requests.get(url, timeout=15, headers=headers)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'xml')
                    entries = soup.find_all('entry')

                    for entry in entries:
                        entry_title = entry.find('title')
                        if entry_title:
                            entry_title_text = entry_title.get_text(strip=True).lower().replace('\n', ' ')
                            title_lower = title.lower()

                            # 제목 유사도 확인 (더 유연하게)
                            title_words = set(title_lower.split())
                            entry_words = set(entry_title_text.split())
                            common_words = title_words & entry_words - stop_words

                            # 공통 단어가 3개 이상이거나, 제목의 핵심 부분이 포함되면 매칭
                            if len(common_words) >= 3 or title_lower[:20] in entry_title_text:
                                id_elem = entry.find('id')
                                if id_elem:
                                    arxiv_url = id_elem.get_text(strip=True)
                                    match = re.search(r'(\d{4}\.\d{4,5})(v\d+)?', arxiv_url)
                                    if match:
                                        arxiv_id = match.group(1)
                                        logger.info(f"arXiv ID 발견: {arxiv_id} (제목: {entry_title_text[:40]}...)")
                                        return arxiv_id

                time.sleep(0.3)  # API 요청 간 딜레이

        except Exception as e:
            logger.debug(f"arXiv 검색 실패: {e}")
        return None

    def find_images_for_paper(
        self,
        paper: Dict,
        min_images: int = 1,
        max_images: int = 5
    ) -> List[Dict]:
        """
        논문에 대한 아키텍처 이미지 찾기 (개선: 더 다양한 소스)

        Args:
            paper: 논문 정보 (title, arxiv_id, url 등)
            min_images: 최소 이미지 개수 (기본값: 1)
            max_images: 최대 이미지 개수 (기본값: 5)

        Returns:
            이미지 정보 리스트 [{"url": "...", "title": "...", "source": "...", "type": "..."}]
        """
        images = []
        seen_urls: Set[str] = set()

        title = paper.get('title', '')
        arxiv_id = paper.get('arxiv_id')

        # arxiv_id가 없으면 제목으로 검색
        if not arxiv_id and title:
            arxiv_id = self._search_arxiv_by_title(title)
            if arxiv_id:
                paper['arxiv_id'] = arxiv_id

        logger.info(f"이미지 검색 시작: {title[:50]}... (arxiv_id: {arxiv_id})")

        # 1. ar5iv (arXiv HTML 버전)에서 Figure 추출 (최우선 - 가장 고품질)
        if arxiv_id:
            ar5iv_images = self._extract_ar5iv_figures(paper)
            for img in ar5iv_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    logger.info(f"  → ar5iv Figure 발견: {img.get('title', '')[:40]}...")
                    if len(images) >= max_images:
                        return images[:max_images]

        # 2. arXiv PDF에서 이미지 추출 (Figure 1, 2 등)
        if len(images) < min_images and arxiv_id and PYMUPDF_AVAILABLE:
            pdf_images = self._extract_pdf_images(paper, max_images=3)
            for img in pdf_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    logger.info(f"  → PDF Figure 추출: {img.get('title', '')[:40]}...")
                    if len(images) >= max_images:
                        return images[:max_images]

        # 3. Papers with Code에서 이미지 찾기
        if len(images) < min_images:
            pw_code_images = self._extract_paperswithcode_images(paper)
            for img in pw_code_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    logger.info(f"  → Papers with Code 이미지: {img.get('title', '')[:40]}...")
                    if len(images) >= max_images:
                        return images[:max_images]

        # 4. Google Custom Search로 이미지 검색 (API 키가 있는 경우)
        if len(images) < min_images and self.google_api_key and self.google_cx:
            # 아키텍처 이미지 검색
            search_images = self._search_google_images_enhanced(paper, max_images - len(images), 'architecture')
            for img in search_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    logger.info(f"  → Google 아키텍처 이미지: {img.get('title', '')[:40]}...")
                    if len(images) >= max_images:
                        return images[:max_images]

            # 실험 결과 이미지 검색
            if len(images) < max_images:
                exp_images = self._search_google_images_enhanced(paper, max_images - len(images), 'experiment')
                for img in exp_images:
                    if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                        seen_urls.add(img['url'])
                        images.append(img)
                        logger.info(f"  → Google 실험결과 이미지: {img.get('title', '')[:40]}...")
                        if len(images) >= max_images:
                            return images[:max_images]

        # 5. Google 이미지 스크래핑 (API 키 없이)
        if len(images) < min_images:
            scrape_images = self._scrape_google_images(paper, max_images - len(images))
            for img in scrape_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    logger.info(f"  → Google 스크래핑 이미지: {img.get('title', '')[:40]}...")
                    if len(images) >= max_images:
                        return images[:max_images]

        # 6. arXiv abs 페이지에서 OG 이미지 등 추출
        if len(images) < min_images and arxiv_id:
            arxiv_images = self._extract_arxiv_images(paper)
            for img in arxiv_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    if len(images) >= max_images:
                        return images[:max_images]

        # 7. 논문 URL에서 직접 이미지 추출
        if len(images) < min_images and paper.get('url'):
            direct_images = self._extract_direct_url_images(paper)
            for img in direct_images:
                if img['url'] not in seen_urls and self._validate_image_url(img['url']):
                    seen_urls.add(img['url'])
                    images.append(img)
                    if len(images) >= max_images:
                        return images[:max_images]

        logger.info(f"이미지 검색 완료: {len(images)}개 발견")
        return images[:max_images]

    def _extract_ar5iv_figures(self, paper: Dict) -> List[Dict]:
        """
        ar5iv.org (arXiv HTML 버전)에서 Figure 이미지 추출

        ar5iv는 arXiv 논문을 HTML로 변환한 사이트로, Figure가 이미지로 제공됨
        """
        images = []
        arxiv_id = paper.get('arxiv_id')

        if not arxiv_id:
            return images

        try:
            # ar5iv URL (arXiv ID에서 버전 제거)
            arxiv_id_clean = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
            ar5iv_url = f"https://ar5iv.org/abs/{arxiv_id_clean}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            logger.debug(f"ar5iv 페이지 요청: {ar5iv_url}")
            response = requests.get(ar5iv_url, timeout=20, headers=headers, allow_redirects=True)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Figure 요소 찾기 (ar5iv는 <figure> 태그 사용)
                figures = soup.find_all('figure')

                for i, figure in enumerate(figures[:10]):  # 최대 10개 Figure 확인
                    # Figure 내 이미지 찾기
                    img_tag = figure.find('img')
                    if not img_tag:
                        continue

                    src = img_tag.get('src', '') or img_tag.get('data-src', '')
                    if not src:
                        continue

                    # 상대 경로를 절대 경로로 변환
                    if src.startswith('//'):
                        img_url = 'https:' + src
                    elif src.startswith('/'):
                        img_url = f"https://ar5iv.org{src}"
                    elif not src.startswith('http'):
                        img_url = urljoin(ar5iv_url, src)
                    else:
                        img_url = src

                    # Figure 캡션 추출
                    figcaption = figure.find('figcaption')
                    caption_text = figcaption.get_text(strip=True)[:100] if figcaption else f"Figure {i+1}"

                    # 이미지 유형 판단
                    caption_lower = caption_text.lower()
                    if any(kw in caption_lower for kw in ['architecture', 'overview', 'framework', 'model', 'structure', 'network']):
                        img_type = 'architecture'
                    elif any(kw in caption_lower for kw in ['result', 'experiment', 'comparison', 'performance', 'accuracy', 'table']):
                        img_type = 'experiment'
                    else:
                        img_type = 'intuitive'

                    images.append({
                        'url': img_url,
                        'title': caption_text,
                        'source': f'ar5iv (Figure {i+1})',
                        'type': img_type
                    })

                    # 아키텍처 이미지를 우선적으로 찾으면 충분
                    if img_type == 'architecture' and len([img for img in images if img['type'] == 'architecture']) >= 2:
                        break

                # Figure가 없으면 일반 이미지 태그에서 찾기
                if not images:
                    img_tags = soup.find_all('img', class_=re.compile(r'ltx_graphics|figure', re.I))
                    for i, img in enumerate(img_tags[:5]):
                        src = img.get('src', '') or img.get('data-src', '')
                        if not src:
                            continue

                        if src.startswith('//'):
                            img_url = 'https:' + src
                        elif src.startswith('/'):
                            img_url = f"https://ar5iv.org{src}"
                        elif not src.startswith('http'):
                            img_url = urljoin(ar5iv_url, src)
                        else:
                            img_url = src

                        alt_text = img.get('alt', f'Figure {i+1}')
                        images.append({
                            'url': img_url,
                            'title': alt_text[:100],
                            'source': f'ar5iv (Image {i+1})',
                            'type': 'architecture'
                        })

        except requests.exceptions.Timeout:
            logger.debug(f"ar5iv 요청 타임아웃: {arxiv_id}")
        except Exception as e:
            logger.debug(f"ar5iv 이미지 추출 실패: {e}")

        return images

    def _extract_pdf_images(self, paper: Dict, max_images: int = 3) -> List[Dict]:
        """
        arXiv PDF에서 아키텍처/개요 이미지 추출 (pymupdf 사용)

        PDF를 다운로드하고 핵심 Figure 이미지를 스마트하게 선별
        """
        images = []
        arxiv_id = paper.get('arxiv_id')
        title = paper.get('title', 'paper')

        if not arxiv_id or not PYMUPDF_AVAILABLE:
            return images

        try:
            arxiv_id_clean = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id_clean}.pdf"

            # 논문별 이미지 저장 폴더 생성
            safe_title = re.sub(r'[^\w\-_]', '_', title)[:50]
            paper_img_dir = self.IMAGE_DIR / safe_title
            paper_img_dir.mkdir(parents=True, exist_ok=True)

            # PDF 임시 저장
            pdf_path = paper_img_dir / "paper.pdf"

            # PDF 다운로드 (캐시 없으면)
            if not pdf_path.exists():
                logger.debug(f"PDF 다운로드 중: {pdf_url}")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                response = requests.get(pdf_url, timeout=30, headers=headers, stream=True)
                if response.status_code == 200:
                    with open(pdf_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                else:
                    logger.debug(f"PDF 다운로드 실패: {response.status_code}")
                    return images

            # PDF에서 이미지 추출
            doc = fitz.open(pdf_path)

            # 모든 이미지 후보 수집 (전체 페이지에서)
            candidates = []

            for page_num in range(min(15, len(doc))):  # 모든 페이지 검색
                page = doc[page_num]
                image_list = page.get_images(full=True)

                for img_index, img_info in enumerate(image_list):
                    xref = img_info[0]

                    try:
                        base_image = doc.extract_image(xref)
                        if not base_image:
                            continue

                        width = base_image.get('width', 0)
                        height = base_image.get('height', 0)
                        img_bytes = base_image.get('image', b'')
                        img_size = len(img_bytes)

                        # 최소 크기 제한 (300x200 이상 - 의미있는 다이어그램)
                        if width < 300 or height < 200:
                            continue

                        # 가로세로 비율 확인 (너무 긴 이미지 제외)
                        aspect_ratio = max(width, height) / min(width, height)
                        if aspect_ratio > 4:
                            continue

                        # 너무 작은 파일 제외 (아이콘/로고)
                        if img_size < 10000:  # 10KB 미만
                            continue

                        # 스코어 계산 (아키텍처 이미지일 가능성)
                        score = 0

                        # 페이지 위치에 따른 점수
                        # 1-5페이지 선호 (보통 아키텍처/개요 Figure가 있음)
                        if 1 <= page_num <= 4:
                            score += 30
                        elif page_num == 0:  # 1페이지도 포함 (큰 Figure가 있을 수 있음)
                            score += 20
                        elif page_num <= 7:
                            score += 15

                        # 적당한 크기의 이미지 선호
                        area = width * height
                        if 100000 < area < 2000000:  # 적당한 크기
                            score += 20
                        elif area >= 2000000:  # 큰 이미지
                            score += 10

                        # 가로가 긴 이미지 선호 (아키텍처 다이어그램)
                        if width > height and 1.2 < aspect_ratio < 3:
                            score += 25

                        # 파일 크기 적당한 것 선호 (30KB-500KB)
                        if 30000 < img_size < 500000:
                            score += 15

                        candidates.append({
                            'page_num': page_num,
                            'img_index': img_index,
                            'width': width,
                            'height': height,
                            'size': img_size,
                            'score': score,
                            'base_image': base_image
                        })

                    except Exception as e:
                        logger.debug(f"이미지 분석 실패 (page {page_num}, img {img_index}): {e}")
                        continue

            # 스코어 순으로 정렬하여 상위 이미지 선택
            candidates.sort(key=lambda x: x['score'], reverse=True)

            for candidate in candidates[:max_images]:
                base_image = candidate['base_image']
                page_num = candidate['page_num']
                img_index = candidate['img_index']

                img_ext = base_image.get('ext', 'png')
                img_filename = f"figure_p{page_num+1}_{img_index+1}.{img_ext}"
                img_path = paper_img_dir / img_filename

                with open(img_path, 'wb') as f:
                    f.write(base_image['image'])

                relative_path = f"images/{safe_title}/{img_filename}"

                images.append({
                    'url': relative_path,
                    'title': f"{title} - Figure (Page {page_num+1})",
                    'source': f'PDF (Page {page_num+1}, Score: {candidate["score"]})',
                    'type': 'architecture',
                    'local_path': str(img_path.absolute()),
                    'dimensions': f"{candidate['width']}x{candidate['height']}"
                })

                logger.debug(f"선택된 이미지: page {page_num+1}, {candidate['width']}x{candidate['height']}, score={candidate['score']}")

            doc.close()

        except Exception as e:
            logger.debug(f"PDF 이미지 추출 실패: {e}")

        return images

    def _extract_arxiv_images(self, paper: Dict) -> List[Dict]:
        """arXiv 논문 페이지에서 이미지 추출"""
        images = []
        arxiv_id = paper.get('arxiv_id')

        if not arxiv_id:
            return images

        try:
            url = f"https://arxiv.org/abs/{arxiv_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=15, headers=headers)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Open Graph 이미지 (메타 태그)
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

        except Exception as e:
            logger.debug(f"arXiv 이미지 추출 실패: {e}")

        return images

    def _search_google_images_enhanced(
        self,
        paper: Dict,
        max_results: int = 3,
        image_type: str = 'architecture'
    ) -> List[Dict]:
        """Google Custom Search API로 이미지 검색"""
        images = []

        if not self.google_api_key or not self.google_cx:
            return images

        title = paper.get('title', '')
        authors = paper.get('authors', [])
        first_author = authors[0] if isinstance(authors, list) and len(authors) > 0 else ''

        # 이미지 유형별 검색 쿼리 생성
        queries = []

        if image_type == 'architecture':
            queries.append(f"{title} architecture diagram")
            queries.append(f"{title} model architecture")
            queries.append(f"{title} network diagram")
            queries.append(f"{title} framework")
        elif image_type == 'experiment':
            queries.append(f"{title} experimental results")
            queries.append(f"{title} performance comparison")
            queries.append(f"{title} results graph")
        else:
            queries.append(f"{title} visualization")
            queries.append(f"{title} overview")

        # 제목에서 약어 추출
        if title:
            abbrev_match = re.search(r'\(([A-Za-z0-9\-]+)\)', title)
            if abbrev_match:
                abbrev = abbrev_match.group(1)
                if image_type == 'architecture':
                    queries.append(f"{abbrev} architecture")
                elif image_type == 'experiment':
                    queries.append(f"{abbrev} results")

        seen_urls = set()
        for query in queries[:4]:
            if len(images) >= max_results:
                break

            try:
                search_url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.google_api_key,
                    'cx': self.google_cx,
                    'q': query,
                    'searchType': 'image',
                    'num': min(5, max_results - len(images)),
                    'safe': 'active',
                    'imgSize': 'large',
                    'fileType': 'jpg,png',
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

                            images.append({
                                'url': img_url,
                                'title': image_title or f"{title} - {image_type.title()}",
                                'source': f'Google ({query[:25]}...)',
                                'type': image_type
                            })
                            if len(images) >= max_results:
                                break

                    time.sleep(0.3)

            except Exception as e:
                logger.debug(f"Google 이미지 검색 실패 ({query[:25]}...): {e}")
                continue

        return images

    def _scrape_google_images(self, paper: Dict, max_results: int = 3) -> List[Dict]:
        """Google 이미지 검색 스크래핑 (API 키 없이)"""
        images = []
        title = paper.get('title', '')

        if not title:
            return images

        # 검색 쿼리 목록
        queries = [
            f"{title} architecture diagram",
            f"{title} model figure",
        ]

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        for query in queries:
            if len(images) >= max_results:
                break

            try:
                search_url = f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch&safe=active"
                response = requests.get(search_url, headers=headers, timeout=15)

                if response.status_code == 200:
                    # 이미지 URL 패턴 찾기
                    # Google 이미지 검색 결과에서 이미지 URL 추출
                    img_patterns = re.findall(r'"(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', response.text, re.I)

                    for img_url in img_patterns[:10]:
                        # 구글 자체 이미지/로고 제외
                        if 'google' in img_url.lower() or 'gstatic' in img_url.lower():
                            continue
                        if len(img_url) < 50:  # 너무 짧은 URL 제외
                            continue

                        images.append({
                            'url': img_url,
                            'title': f"{title} - Architecture",
                            'source': 'Google Images',
                            'type': 'architecture'
                        })

                        if len(images) >= max_results:
                            break

                time.sleep(0.5)  # 요청 간 딜레이

            except Exception as e:
                logger.debug(f"Google 이미지 스크래핑 실패: {e}")
                continue

        return images

    def _extract_paperswithcode_images(self, paper: Dict) -> List[Dict]:
        """Papers with Code에서 이미지 추출"""
        images = []
        title = paper.get('title', '')

        if not title:
            return images

        try:
            search_query = quote_plus(title[:100])
            search_url = f"https://paperswithcode.com/search?q={search_query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(search_url, timeout=15, headers=headers, allow_redirects=True)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 논문 카드에서 이미지 찾기
                paper_cards = soup.find_all('div', class_=re.compile(r'paper-card|entity|row', re.I))

                for card in paper_cards[:5]:
                    img_tags = card.find_all('img')
                    for img in img_tags:
                        src = img.get('src', '') or img.get('data-src', '')
                        if src and ('paper' in src.lower() or 'media' in src.lower()):
                            full_url = src if src.startswith('http') else urljoin('https://paperswithcode.com', src)
                            images.append({
                                'url': full_url,
                                'title': f"{title} - Papers with Code",
                                'source': 'Papers with Code',
                                'type': 'architecture'
                            })
                            if len(images) >= 2:
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

                # 주요 이미지 태그 찾기
                img_tags = soup.find_all('img')
                for img in img_tags[:10]:
                    src = img.get('src', '') or img.get('data-src', '')
                    if not src:
                        continue

                    alt_text = img.get('alt', '').lower()
                    if any(keyword in alt_text for keyword in ['architecture', 'diagram', 'figure', 'model', 'network']):
                        full_url = src if src.startswith('http') else urljoin(paper_url, src)
                        images.append({
                            'url': full_url,
                            'title': alt_text or f"{paper.get('title', 'Paper')} - Diagram",
                            'source': 'Paper URL',
                            'type': 'architecture'
                        })
                        if len(images) >= 2:
                            break

        except Exception as e:
            logger.debug(f"직접 URL 이미지 추출 실패: {e}")

        return images

    def _validate_image_url(self, url: str) -> bool:
        """이미지 URL 유효성 검증"""
        if not url or len(url) < 5:
            return False

        # 상대 경로 허용 (images/...)
        if url.startswith('images/'):
            return True

        try:
            parsed = urlparse(url)
            if not parsed.scheme or parsed.scheme not in ['http', 'https']:
                return False
            if not parsed.netloc:
                return False
        except Exception:
            return False

        return True


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

    # 이미지를 유형별로 분류
    arch_images = [img for img in images if img.get('type') == 'architecture']
    exp_images = [img for img in images if img.get('type') == 'experiment']
    other_images = [img for img in images if img.get('type') not in ['architecture', 'experiment']]

    # 이미지 마크다운 형식 생성
    def create_image_block(img: Dict) -> List[str]:
        title = img.get('title', '이미지')
        url = img.get('url', '')

        if url:
            lines = [f"![{title}]({url})"]
            if img.get('source'):
                lines.append(f"*출처: {img['source']}*")
            return lines
        return []

    lines = content.split('\n')
    inserted_count = 0

    # 1. 아키텍처 이미지: "방법", "아키텍처", "구조" 관련 섹션 뒤
    if arch_images:
        for i, line in enumerate(lines):
            if line.startswith('##') and not line.startswith('###'):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['방법', '해결', '아키텍처', '구조', 'method', 'approach', 'architecture', 'key idea', '핵심']):
                    insert_pos = min(i + 8, len(lines))
                    img_block = create_image_block(arch_images[0])
                    for img_line in reversed(img_block):
                        lines.insert(insert_pos, img_line)
                    lines.insert(insert_pos, '')  # 빈 줄 추가
                    inserted_count += 1
                    arch_images = arch_images[1:]
                    break

    # 2. 실험 결과 이미지: "실험", "결과" 관련 섹션 뒤
    if exp_images:
        for i, line in enumerate(lines):
            if line.startswith('##') and not line.startswith('###'):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['실험', '결과', 'experiment', 'result', 'evaluation', '평가']):
                    insert_pos = min(i + 8, len(lines))
                    img_block = create_image_block(exp_images[0])
                    for img_line in reversed(img_block):
                        lines.insert(insert_pos, img_line)
                    lines.insert(insert_pos, '')
                    inserted_count += 1
                    exp_images = exp_images[1:]
                    break

    # 3. 추가 아키텍처 이미지가 있으면 다른 섹션에 삽입
    remaining_images = arch_images + exp_images + other_images
    if remaining_images and inserted_count < 3:
        for i, line in enumerate(lines):
            if inserted_count >= 3:
                break
            if line.startswith('##') and not line.startswith('###') and i > 10:
                insert_pos = min(i + 8, len(lines))
                img_block = create_image_block(remaining_images[0])
                for img_line in reversed(img_block):
                    lines.insert(insert_pos, img_line)
                lines.insert(insert_pos, '')
                inserted_count += 1
                remaining_images = remaining_images[1:]

    # 이미지가 하나도 삽입되지 않았으면 첫 번째 섹션 뒤에 추가
    if inserted_count == 0 and images:
        for i, line in enumerate(lines):
            if line.startswith('##') and not line.startswith('###'):
                insert_pos = min(i + 8, len(lines))
                img_block = create_image_block(images[0])
                for img_line in reversed(img_block):
                    lines.insert(insert_pos, img_line)
                lines.insert(insert_pos, '')
                break

    return '\n'.join(lines)
