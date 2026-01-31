"""
다양한 논문 소스에서 최신 논문을 검색하는 통합 검색기

지원 소스:
- arXiv API (프리프린트)
- Semantic Scholar API (인용수, 영향력)
- Papers With Code (트렌딩, 코드 포함)
- Hugging Face Daily Papers (ML 커뮤니티 큐레이션)
- OpenAlex API (오픈 학술 데이터)
- DBLP (컴퓨터 과학)
- CrossRef API (DOI 메타데이터)
"""

import requests
import random
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from abc import ABC, abstractmethod
import xml.etree.ElementTree as ET
import time
import hashlib

logger = logging.getLogger(__name__)

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent


class PaperSource(ABC):
    """논문 소스 추상 클래스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """소스 이름"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """소스 설명"""
        pass

    @abstractmethod
    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        """논문 검색"""
        pass


class ArxivSource(PaperSource):
    """arXiv API를 통한 최신 논문 검색"""

    BASE_URL = "http://export.arxiv.org/api/query"

    # 분야별 arXiv 카테고리 매핑
    CATEGORY_MAP = {
        "Computer Vision": ["cs.CV", "cs.GR"],
        "NLP & Language Models": ["cs.CL", "cs.IR"],
        "Reinforcement Learning": ["cs.LG", "cs.AI"],
        "Generative Models": ["cs.LG", "cs.CV", "stat.ML"],
        "Graph Neural Networks": ["cs.LG", "cs.SI"],
        "Optimization & Training": ["cs.LG", "stat.ML"],
        "Robotics & Embodied AI": ["cs.RO", "cs.AI"],
        "Audio & Speech": ["cs.SD", "eess.AS", "cs.CL"],
        "Multimodal Learning": ["cs.CV", "cs.CL", "cs.MM"],
        "AI Safety & Alignment": ["cs.AI", "cs.CY", "cs.LG"],
    }

    @property
    def name(self) -> str:
        return "arXiv"

    @property
    def description(self) -> str:
        return "최신 AI/ML 프리프린트"

    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        try:
            # arXiv 카테고리 가져오기
            arxiv_cats = self.CATEGORY_MAP.get(category, ["cs.LG", "cs.AI"])
            cat_query = " OR ".join([f"cat:{cat}" for cat in arxiv_cats])

            # 키워드 쿼리 (랜덤 선택으로 다양성 확보)
            selected_keywords = random.sample(keywords, min(3, len(keywords)))
            keyword_query = " OR ".join([f"all:{kw}" for kw in selected_keywords])

            # 날짜 기반 랜덤성 추가 (최근 7-30일 중 랜덤)
            days_back = random.randint(1, 14)

            query = f"({cat_query}) AND ({keyword_query})"

            params = {
                "search_query": query,
                "start": random.randint(0, 20),  # 시작 위치 랜덤
                "max_results": count * 2,  # 여유분 확보
                "sortBy": random.choice(["submittedDate", "relevance", "lastUpdatedDate"]),
                "sortOrder": "descending"
            }

            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()

            papers = self._parse_response(response.text, category)
            random.shuffle(papers)  # 결과 섞기
            return papers[:count]

        except Exception as e:
            logger.warning(f"arXiv 검색 실패: {e}")
            return []

    def _parse_response(self, xml_text: str, category: str) -> List[Dict]:
        papers = []
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            try:
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")

                # 저자 정보
                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text)

                # 발행일
                published = entry.find("atom:published", ns).text[:10]
                year = int(published[:4])

                # arXiv ID
                arxiv_id = entry.find("atom:id", ns).text.split("/abs/")[-1]

                # PDF 링크
                pdf_link = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                papers.append({
                    "title": title,
                    "authors": authors[:5],  # 상위 5명
                    "year": year,
                    "abstract": summary[:500] + "..." if len(summary) > 500 else summary,
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "pdf_url": pdf_link,
                    "source": "arXiv",
                    "arxiv_id": arxiv_id,
                    "searched_category": category,
                    "citations": 0,  # arXiv는 인용수 없음
                })
            except Exception as e:
                logger.debug(f"arXiv 항목 파싱 실패: {e}")
                continue

        return papers


class SemanticScholarSource(PaperSource):
    """Semantic Scholar API를 통한 논문 검색 (인용수 포함)"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    CATEGORY_KEYWORDS = {
        "Computer Vision": ["computer vision", "image recognition", "object detection", "visual"],
        "NLP & Language Models": ["natural language processing", "language model", "transformer", "BERT", "GPT"],
        "Reinforcement Learning": ["reinforcement learning", "policy gradient", "Q-learning", "reward"],
        "Generative Models": ["generative model", "diffusion", "GAN", "VAE", "image generation"],
        "Graph Neural Networks": ["graph neural network", "GNN", "node embedding", "graph learning"],
        "Optimization & Training": ["optimization", "training", "gradient descent", "learning rate"],
        "Robotics & Embodied AI": ["robotics", "robot learning", "manipulation", "navigation"],
        "Audio & Speech": ["speech recognition", "audio processing", "TTS", "ASR"],
        "Multimodal Learning": ["multimodal", "vision-language", "cross-modal", "CLIP"],
        "AI Safety & Alignment": ["AI safety", "alignment", "interpretability", "fairness"],
    }

    @property
    def name(self) -> str:
        return "Semantic Scholar"

    @property
    def description(self) -> str:
        return "인용수 및 영향력 정보 포함"

    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        try:
            # 카테고리 키워드 + 사용자 키워드 조합
            cat_keywords = self.CATEGORY_KEYWORDS.get(category, ["machine learning"])
            all_keywords = list(set(keywords + cat_keywords))

            # 랜덤 키워드 조합으로 다양성 확보
            selected = random.sample(all_keywords, min(3, len(all_keywords)))
            query = " ".join(selected)

            # 연도 필터 (최근 1-2년)
            current_year = datetime.now().year
            year_filter = f"{current_year - 1}-{current_year}"

            params = {
                "query": query,
                "limit": count * 2,
                "offset": random.randint(0, 10),
                "fields": "title,authors,year,abstract,citationCount,url,externalIds,venue",
                "year": year_filter,
            }

            headers = {"Accept": "application/json"}

            response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            papers = self._parse_response(data.get("data", []), category)
            random.shuffle(papers)
            return papers[:count]

        except Exception as e:
            logger.warning(f"Semantic Scholar 검색 실패: {e}")
            return []

    def _parse_response(self, data: List[Dict], category: str) -> List[Dict]:
        papers = []

        for item in data:
            try:
                if not item.get("title"):
                    continue

                authors = [a.get("name", "") for a in item.get("authors", [])[:5]]

                # arXiv ID 또는 DOI
                external_ids = item.get("externalIds", {})
                arxiv_id = external_ids.get("ArXiv")
                doi = external_ids.get("DOI")

                pdf_url = None
                if arxiv_id:
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                papers.append({
                    "title": item.get("title", ""),
                    "authors": authors,
                    "year": item.get("year", datetime.now().year),
                    "abstract": item.get("abstract", "")[:500] if item.get("abstract") else "",
                    "url": item.get("url", ""),
                    "pdf_url": pdf_url,
                    "source": "Semantic Scholar",
                    "citations": item.get("citationCount", 0),
                    "venue": item.get("venue", ""),
                    "searched_category": category,
                    "arxiv_id": arxiv_id,
                    "doi": doi,
                })
            except Exception as e:
                logger.debug(f"Semantic Scholar 항목 파싱 실패: {e}")
                continue

        return papers


class PapersWithCodeSource(PaperSource):
    """Papers With Code API를 통한 트렌딩 논문 검색"""

    BASE_URL = "https://paperswithcode.com/api/v1"

    @property
    def name(self) -> str:
        return "Papers With Code"

    @property
    def description(self) -> str:
        return "트렌딩 논문 + 코드 구현"

    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        try:
            # 트렌딩 논문 또는 키워드 검색
            search_type = random.choice(["trending", "search"])

            if search_type == "trending":
                return self._get_trending(category, count)
            else:
                return self._search_papers(category, keywords, count)

        except Exception as e:
            logger.warning(f"Papers With Code 검색 실패: {e}")
            return []

    def _get_trending(self, category: str, count: int) -> List[Dict]:
        """트렌딩 논문 가져오기"""
        url = f"{self.BASE_URL}/papers/"
        params = {
            "ordering": "-trending_score",
            "page": random.randint(1, 3),
            "items_per_page": count * 2,
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()
        return self._parse_response(data.get("results", []), category)[:count]

    def _search_papers(self, category: str, keywords: List[str], count: int) -> List[Dict]:
        """키워드 검색"""
        url = f"{self.BASE_URL}/papers/"

        selected = random.sample(keywords, min(2, len(keywords)))
        query = " ".join(selected)

        params = {
            "q": query,
            "page": 1,
            "items_per_page": count * 2,
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()
        papers = self._parse_response(data.get("results", []), category)
        random.shuffle(papers)
        return papers[:count]

    def _parse_response(self, data: List[Dict], category: str) -> List[Dict]:
        papers = []

        for item in data:
            try:
                papers.append({
                    "title": item.get("title", ""),
                    "authors": item.get("authors", [])[:5] if isinstance(item.get("authors"), list) else [],
                    "year": self._extract_year(item.get("published", "")),
                    "abstract": item.get("abstract", "")[:500] if item.get("abstract") else "",
                    "url": item.get("url_abs", "") or item.get("paper_url", ""),
                    "pdf_url": item.get("url_pdf", ""),
                    "source": "Papers With Code",
                    "citations": 0,
                    "searched_category": category,
                    "code_url": item.get("proceeding", ""),
                    "has_code": True,
                })
            except Exception as e:
                logger.debug(f"Papers With Code 항목 파싱 실패: {e}")
                continue

        return papers

    def _extract_year(self, date_str: str) -> int:
        if not date_str:
            return datetime.now().year
        try:
            return int(date_str[:4])
        except:
            return datetime.now().year


class HuggingFacePapersSource(PaperSource):
    """Hugging Face Daily Papers 검색"""

    BASE_URL = "https://huggingface.co/api/daily_papers"

    @property
    def name(self) -> str:
        return "Hugging Face"

    @property
    def description(self) -> str:
        return "ML 커뮤니티 큐레이션"

    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        try:
            # 최근 며칠 중 랜덤 선택
            days_back = random.randint(0, 7)
            target_date = datetime.now() - timedelta(days=days_back)
            date_str = target_date.strftime("%Y-%m-%d")

            response = requests.get(f"{self.BASE_URL}?date={date_str}", timeout=15)
            response.raise_for_status()

            data = response.json()
            papers = self._parse_response(data, category, keywords)

            # 키워드 관련성으로 필터링
            if keywords:
                papers = self._filter_by_keywords(papers, keywords)

            random.shuffle(papers)
            return papers[:count]

        except Exception as e:
            logger.warning(f"Hugging Face 검색 실패: {e}")
            return []

    def _parse_response(self, data: List[Dict], category: str, keywords: List[str]) -> List[Dict]:
        papers = []

        for item in data:
            try:
                paper_info = item.get("paper", {})

                papers.append({
                    "title": paper_info.get("title", ""),
                    "authors": [a.get("name", "") for a in paper_info.get("authors", [])[:5]],
                    "year": datetime.now().year,
                    "abstract": paper_info.get("summary", "")[:500] if paper_info.get("summary") else "",
                    "url": f"https://huggingface.co/papers/{paper_info.get('id', '')}",
                    "pdf_url": "",
                    "source": "Hugging Face",
                    "citations": item.get("numComments", 0),
                    "searched_category": category,
                    "upvotes": item.get("paper", {}).get("upvotes", 0),
                })
            except Exception as e:
                logger.debug(f"Hugging Face 항목 파싱 실패: {e}")
                continue

        return papers

    def _filter_by_keywords(self, papers: List[Dict], keywords: List[str]) -> List[Dict]:
        """키워드 관련성으로 필터링"""
        keyword_lower = [kw.lower() for kw in keywords]

        scored_papers = []
        for paper in papers:
            title_lower = paper.get("title", "").lower()
            abstract_lower = paper.get("abstract", "").lower()

            score = sum(1 for kw in keyword_lower if kw in title_lower or kw in abstract_lower)
            scored_papers.append((score, paper))

        # 점수순 정렬 후 반환
        scored_papers.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored_papers]


class OpenAlexSource(PaperSource):
    """OpenAlex API를 통한 오픈 학술 데이터 검색"""

    BASE_URL = "https://api.openalex.org/works"

    CONCEPT_IDS = {
        "Computer Vision": "C31972630",
        "NLP & Language Models": "C204321447",
        "Reinforcement Learning": "C119857082",
        "Generative Models": "C154945302",
        "Graph Neural Networks": "C50644808",
        "Optimization & Training": "C119857082",
        "Robotics & Embodied AI": "C90856448",
        "Audio & Speech": "C38652104",
        "Multimodal Learning": "C41008148",
        "AI Safety & Alignment": "C154945302",
    }

    @property
    def name(self) -> str:
        return "OpenAlex"

    @property
    def description(self) -> str:
        return "오픈 학술 메타데이터"

    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        try:
            # 최근 논문 필터
            current_year = datetime.now().year
            from_date = f"{current_year - 1}-01-01"

            # 키워드 검색 쿼리
            selected = random.sample(keywords, min(3, len(keywords)))
            search_query = " ".join(selected)

            params = {
                "search": search_query,
                "filter": f"from_publication_date:{from_date},type:article",
                "sort": random.choice(["cited_by_count:desc", "publication_date:desc", "relevance_score:desc"]),
                "per_page": count * 2,
                "page": random.randint(1, 3),
            }

            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            papers = self._parse_response(data.get("results", []), category)
            random.shuffle(papers)
            return papers[:count]

        except Exception as e:
            logger.warning(f"OpenAlex 검색 실패: {e}")
            return []

    def _parse_response(self, data: List[Dict], category: str) -> List[Dict]:
        papers = []

        for item in data:
            try:
                # 저자 정보
                authors = []
                for authorship in item.get("authorships", [])[:5]:
                    author = authorship.get("author", {})
                    if author.get("display_name"):
                        authors.append(author["display_name"])

                # 발행 연도
                year = item.get("publication_year", datetime.now().year)

                # PDF URL (Open Access인 경우)
                pdf_url = None
                oa_info = item.get("open_access", {})
                if oa_info.get("is_oa"):
                    pdf_url = oa_info.get("oa_url")

                papers.append({
                    "title": item.get("title", ""),
                    "authors": authors,
                    "year": year,
                    "abstract": "",  # OpenAlex는 abstract가 별도 요청 필요
                    "url": item.get("id", "").replace("https://openalex.org/", "https://openalex.org/works/"),
                    "pdf_url": pdf_url,
                    "source": "OpenAlex",
                    "citations": item.get("cited_by_count", 0),
                    "searched_category": category,
                    "doi": item.get("doi", ""),
                })
            except Exception as e:
                logger.debug(f"OpenAlex 항목 파싱 실패: {e}")
                continue

        return papers


class DBLPSource(PaperSource):
    """DBLP API를 통한 컴퓨터 과학 논문 검색"""

    BASE_URL = "https://dblp.org/search/publ/api"

    @property
    def name(self) -> str:
        return "DBLP"

    @property
    def description(self) -> str:
        return "컴퓨터 과학 출판물"

    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        try:
            # 키워드 조합
            selected = random.sample(keywords, min(3, len(keywords)))
            query = " ".join(selected)

            params = {
                "q": query,
                "format": "json",
                "h": count * 2,
                "f": random.randint(0, 20),
            }

            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            hits = data.get("result", {}).get("hits", {}).get("hit", [])

            papers = self._parse_response(hits, category)
            random.shuffle(papers)
            return papers[:count]

        except Exception as e:
            logger.warning(f"DBLP 검색 실패: {e}")
            return []

    def _parse_response(self, hits: List[Dict], category: str) -> List[Dict]:
        papers = []

        for hit in hits:
            try:
                info = hit.get("info", {})

                # 저자 처리 (단일 또는 다중)
                authors_raw = info.get("authors", {}).get("author", [])
                if isinstance(authors_raw, str):
                    authors = [authors_raw]
                elif isinstance(authors_raw, list):
                    authors = [a if isinstance(a, str) else a.get("text", "") for a in authors_raw][:5]
                else:
                    authors = []

                # 연도 추출
                year = int(info.get("year", datetime.now().year))

                papers.append({
                    "title": info.get("title", ""),
                    "authors": authors,
                    "year": year,
                    "abstract": "",  # DBLP는 abstract 미제공
                    "url": info.get("url", ""),
                    "pdf_url": info.get("ee", ""),
                    "source": "DBLP",
                    "citations": 0,
                    "searched_category": category,
                    "venue": info.get("venue", ""),
                })
            except Exception as e:
                logger.debug(f"DBLP 항목 파싱 실패: {e}")
                continue

        return papers


class CrossRefSource(PaperSource):
    """CrossRef API를 통한 DOI 기반 논문 검색"""

    BASE_URL = "https://api.crossref.org/works"

    @property
    def name(self) -> str:
        return "CrossRef"

    @property
    def description(self) -> str:
        return "DOI 기반 학술 메타데이터"

    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        try:
            selected = random.sample(keywords, min(3, len(keywords)))
            query = " ".join(selected)

            # 최근 연도 필터
            current_year = datetime.now().year

            params = {
                "query": query,
                "rows": count * 2,
                "offset": random.randint(0, 20),
                "filter": f"from-pub-date:{current_year - 1}",
                "sort": random.choice(["relevance", "published", "is-referenced-by-count"]),
            }

            headers = {"User-Agent": "TistoryAutoPoster/1.0 (mailto:example@example.com)"}

            response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            items = data.get("message", {}).get("items", [])

            papers = self._parse_response(items, category)
            random.shuffle(papers)
            return papers[:count]

        except Exception as e:
            logger.warning(f"CrossRef 검색 실패: {e}")
            return []

    def _parse_response(self, items: List[Dict], category: str) -> List[Dict]:
        papers = []

        for item in items:
            try:
                # 제목 추출
                title_list = item.get("title", [])
                title = title_list[0] if title_list else ""

                # 저자 추출
                authors = []
                for author in item.get("author", [])[:5]:
                    name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                    if name:
                        authors.append(name)

                # 연도 추출
                pub_date = item.get("published", {}).get("date-parts", [[datetime.now().year]])
                year = pub_date[0][0] if pub_date and pub_date[0] else datetime.now().year

                # DOI 및 URL
                doi = item.get("DOI", "")
                url = f"https://doi.org/{doi}" if doi else ""

                papers.append({
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "abstract": item.get("abstract", "")[:500] if item.get("abstract") else "",
                    "url": url,
                    "pdf_url": "",
                    "source": "CrossRef",
                    "citations": item.get("is-referenced-by-count", 0),
                    "searched_category": category,
                    "doi": doi,
                    "venue": item.get("container-title", [""])[0] if item.get("container-title") else "",
                })
            except Exception as e:
                logger.debug(f"CrossRef 항목 파싱 실패: {e}")
                continue

        return papers


class MoonlightSource(PaperSource):
    """Moonlight 논문 큐레이션 플랫폼 검색 (한국어 리뷰 포함)"""

    BASE_URL = "https://www.themoonlight.io/api/review/latest"

    # 분야 코드 매핑
    CATEGORY_MAP = {
        "Computer Vision": "cs",
        "NLP & Language Models": "cs",
        "Reinforcement Learning": "cs",
        "Generative Models": "cs",
        "Graph Neural Networks": "cs",
        "Optimization & Training": "cs",
        "Robotics & Embodied AI": "cs",
        "Audio & Speech": "cs",
        "Multimodal Learning": "cs",
        "AI Safety & Alignment": "cs",
        "LLM & Reasoning": "cs",
        "AI Agents": "cs",
        "Code Generation": "cs",
        "RAG & Knowledge": "cs",
        "Vision-Language Models": "cs",
        "Video & World Models": "cs",
        "3D & Spatial AI": "cs",
        "Image Generation": "cs",
        "Efficient AI": "cs",
        "Scientific AI": "cs",
    }

    @property
    def name(self) -> str:
        return "Moonlight"

    @property
    def description(self) -> str:
        return "한국어 논문 리뷰 큐레이션"

    def search(self, category: str, keywords: List[str], count: int = 5) -> List[Dict]:
        try:
            # 카테고리 매핑 (대부분 cs)
            moonlight_cat = self.CATEGORY_MAP.get(category, "cs")

            params = {
                "limit": count * 3,  # 여유분 확보
                "offset": random.randint(0, 20),  # 다양성을 위한 오프셋
                "language": "ko",
                "category": moonlight_cat,
            }

            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()
            papers = self._parse_response(data.get("results", []), category, keywords)

            # 키워드 관련성으로 필터링
            if keywords:
                papers = self._filter_by_keywords(papers, keywords)

            random.shuffle(papers)
            return papers[:count]

        except Exception as e:
            logger.warning(f"Moonlight 검색 실패: {e}")
            return []

    def _parse_response(self, data: List[Dict], category: str, keywords: List[str]) -> List[Dict]:
        papers = []

        for item in data:
            try:
                # 발행일 파싱
                pub_date = item.get("published_date", "")
                year = datetime.now().year
                if pub_date:
                    try:
                        year = int(pub_date[:4])
                    except:
                        pass

                # arXiv ID 추출 (URL에서)
                url = item.get("url", "")
                arxiv_id = ""
                if "arxiv.org" in url:
                    arxiv_id = url.split("/")[-1].replace("v1", "").replace("v2", "")

                papers.append({
                    "title": item.get("title", ""),
                    "authors": item.get("authors", [])[:5],
                    "year": year,
                    "abstract": item.get("summary", "")[:500] if item.get("summary") else "",
                    "url": url,
                    "pdf_url": item.get("pdf_url", ""),
                    "source": "Moonlight",
                    "citations": 0,
                    "searched_category": category,
                    "arxiv_id": arxiv_id,
                    "keywords_short": item.get("keywords_short", ""),
                    "moonlight_slug": item.get("slug", ""),
                    "moonlight_url": f"https://www.themoonlight.io/ko/review/{item.get('slug', '')}",
                })
            except Exception as e:
                logger.debug(f"Moonlight 항목 파싱 실패: {e}")
                continue

        return papers

    def _filter_by_keywords(self, papers: List[Dict], keywords: List[str]) -> List[Dict]:
        """키워드 관련성으로 필터링"""
        keyword_lower = [kw.lower() for kw in keywords]

        scored_papers = []
        for paper in papers:
            title_lower = paper.get("title", "").lower()
            abstract_lower = paper.get("abstract", "").lower()
            keywords_short = paper.get("keywords_short", "").lower()

            score = sum(1 for kw in keyword_lower
                       if kw in title_lower or kw in abstract_lower or kw in keywords_short)
            scored_papers.append((score, paper))

        # 점수순 정렬 후 반환
        scored_papers.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored_papers]


class PaperSearcher:
    """
    다양한 논문 소스를 통합하는 검색기

    랜덤으로 소스를 선택하여 매일 다른 결과를 제공
    """

    def __init__(self):
        # Moonlight + Hugging Face 중 랜덤 선택
        self.sources: List[PaperSource] = [
            MoonlightSource(),          # 한국어 논문 리뷰 큐레이션
            HuggingFacePapersSource(),  # ML 커뮤니티 큐레이션
        ]

        # 소스별 가중치 (동일하게 설정하여 50:50 확률)
        self.source_weights = {
            "Moonlight": 1,
            "Hugging Face": 1,
        }

        # 검색 히스토리 (중복 방지용)
        self.search_history: Dict[str, set] = {}

    def get_available_sources(self) -> List[str]:
        """사용 가능한 소스 목록 반환"""
        return [source.name for source in self.sources]

    def search(
        self,
        category: str,
        keywords: List[str],
        count: int = 5,
        source_count: int = 1,  # 랜덤으로 1개 소스만 선택
        exclude_titles: List[str] = None,
        retry_on_failure: bool = True
    ) -> List[Dict]:
        """
        Moonlight/Hugging Face 중 랜덤으로 1개 소스 선택하여 논문 검색

        Args:
            category: 검색 분야
            keywords: 키워드 목록
            count: 총 논문 수
            source_count: 사용할 소스 수
            exclude_titles: 제외할 논문 제목 목록
            retry_on_failure: 실패 시 다른 소스로 재시도 여부

        Returns:
            논문 정보 리스트
        """
        exclude_titles = set(t.lower() for t in (exclude_titles or []))

        all_papers = []
        used_sources = []
        failed_sources = set()

        # 신뢰도 순으로 정렬된 소스 목록
        priority_sources = self._get_priority_sources()

        # 초기 소스 선택
        selected_sources = self._select_sources(source_count)
        sources_to_try = list(selected_sources)

        max_attempts = len(self.sources) if retry_on_failure else source_count
        attempt = 0

        while len(all_papers) < count and attempt < max_attempts:
            attempt += 1

            # 시도할 소스가 없으면 우선순위 소스에서 추가
            if not sources_to_try:
                for src in priority_sources:
                    if src.name not in failed_sources and src.name not in used_sources:
                        sources_to_try.append(src)
                        break

            if not sources_to_try:
                break  # 더 이상 시도할 소스 없음

            source = sources_to_try.pop(0)

            # 이미 실패한 소스는 건너뛰기
            if source.name in failed_sources:
                continue

            # 필요한 논문 수 계산
            needed = count - len(all_papers)
            per_source = max(2, needed + 1)  # 여유분 확보

            try:
                logger.info(f"[{source.name}] 검색 시도 중...")
                papers = source.search(category, keywords, per_source)

                if papers:
                    # 중복 제거
                    for paper in papers:
                        title_lower = paper.get("title", "").lower()
                        if title_lower and title_lower not in exclude_titles:
                            if not any(p.get("title", "").lower() == title_lower for p in all_papers):
                                all_papers.append(paper)
                                exclude_titles.add(title_lower)

                                if len(all_papers) >= count:
                                    break

                    used_sources.append(source.name)
                    logger.info(f"[{source.name}] {len(papers)}개 논문 검색 성공")
                else:
                    logger.warning(f"[{source.name}] 검색 결과 없음")
                    failed_sources.add(source.name)

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    logger.warning(f"[{source.name}] 레이트 리밋 초과, 다른 소스 시도")
                elif "timeout" in error_msg.lower():
                    logger.warning(f"[{source.name}] 타임아웃, 다른 소스 시도")
                else:
                    logger.warning(f"[{source.name}] 검색 실패: {e}")

                failed_sources.add(source.name)
                continue

            # API 레이트 리밋 방지
            time.sleep(0.3)

        # 결과 섞기 및 개수 제한
        random.shuffle(all_papers)
        result = all_papers[:count]

        # 사용된 소스 정보 추가
        for paper in result:
            paper["search_sources"] = used_sources

        if len(result) < count:
            logger.warning(f"요청 {count}개 중 {len(result)}개만 검색됨 (사용 소스: {used_sources})")
        else:
            logger.info(f"총 {len(result)}개 논문 검색 완료 (소스: {used_sources})")

        return result

    def _select_sources(self, count: int) -> List[PaperSource]:
        """가중치 기반으로 소스 랜덤 선택"""
        # 가중치 리스트 생성
        weighted_sources = []
        for source in self.sources:
            weight = self.source_weights.get(source.name, 1)
            weighted_sources.extend([source] * weight)

        # 랜덤 선택 (중복 방지)
        selected = []
        available = list(set(weighted_sources))
        random.shuffle(available)

        for source in available:
            if len(selected) >= count:
                break
            if source not in selected:
                selected.append(source)

        return selected

    def _get_priority_sources(self) -> List[PaperSource]:
        """신뢰도 순으로 정렬된 소스 목록 반환"""
        # Moonlight > Hugging Face
        priority_order = {
            "Moonlight": 0,          # 한국어 논문 리뷰 큐레이션 (최우선)
            "Hugging Face": 1,       # ML 커뮤니티 큐레이션
        }
        return sorted(self.sources, key=lambda s: priority_order.get(s.name, 99))

    def search_single_source(
        self,
        source_name: str,
        category: str,
        keywords: List[str],
        count: int = 5
    ) -> List[Dict]:
        """특정 소스에서만 검색"""
        for source in self.sources:
            if source.name == source_name:
                return source.search(category, keywords, count)

        logger.warning(f"알 수 없는 소스: {source_name}")
        return []

    def get_diverse_papers(
        self,
        category: str,
        keywords: List[str],
        count: int = 5,
        previous_titles: List[str] = None
    ) -> List[Dict]:
        """
        다양성을 보장하는 논문 검색

        - 여러 소스에서 가져오기
        - 이전 검색 결과와 중복 방지
        - 키워드 조합 다양화
        """
        previous_titles = previous_titles or []

        # 날짜 기반 시드로 일관된 랜덤성
        date_seed = datetime.now().strftime("%Y%m%d")
        category_hash = hashlib.md5(category.encode()).hexdigest()[:8]
        random.seed(f"{date_seed}_{category_hash}")

        # 다양한 소스에서 검색
        papers = self.search(
            category=category,
            keywords=keywords,
            count=count,
            source_count=3,  # 3개 소스 사용
            exclude_titles=previous_titles
        )

        # 시드 리셋
        random.seed()

        return papers

    def search_latest_papers(
        self,
        fields: List[str],
        count_per_field: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        분야별 최신 논문 검색 (GUI용) - 요청 개수 보장

        Args:
            fields: 검색할 분야 코드 리스트
            count_per_field: 분야당 검색할 논문 수

        Returns:
            분야별 논문 리스트 딕셔너리
        """
        # 분야 코드 → 카테고리 이름 매핑 (2024-2025 최신 트렌드 반영)
        field_to_category = {
            # LLM & 추론
            "llm_reasoning": "LLM & Reasoning",
            "ai_agents": "AI Agents",
            "code_generation": "Code Generation",
            "rag_knowledge": "RAG & Knowledge",
            # 비전 & 멀티모달
            "computer_vision": "Computer Vision",
            "vision_language": "Vision-Language Models",
            "video_world": "Video & World Models",
            "3d_spatial": "3D & Spatial AI",
            # 생성 모델
            "image_generation": "Image Generation",
            "audio_speech": "Audio & Speech",
            # 학습 & 최적화
            "reinforcement_learning": "Reinforcement Learning",
            "efficient_ai": "Efficient AI",
            # 응용 & 안전
            "robotics": "Robotics & Embodied AI",
            "scientific_ai": "Scientific AI",
            "ai_safety": "AI Safety & Alignment",
        }

        # 분야별 키워드 (정밀한 검색을 위한 풍부한 키워드)
        field_keywords = {
            # LLM & 추론
            "llm_reasoning": ["large language model", "LLM", "GPT-4", "Claude", "Llama", "chain-of-thought", "reasoning", "in-context learning", "prompting", "instruction tuning"],
            "ai_agents": ["AI agent", "autonomous agent", "tool use", "function calling", "multi-agent", "agent framework", "agentic", "planning agent"],
            "code_generation": ["code generation", "code synthesis", "program synthesis", "Copilot", "code LLM", "automated programming", "code completion"],
            "rag_knowledge": ["retrieval augmented", "RAG", "knowledge retrieval", "dense retrieval", "vector database", "knowledge base", "embedding retrieval"],
            # 비전 & 멀티모달
            "computer_vision": ["computer vision", "object detection", "image segmentation", "image classification", "visual recognition", "ViT", "CNN", "YOLO"],
            "vision_language": ["vision-language", "VLM", "GPT-4V", "multimodal LLM", "CLIP", "image-text", "visual question answering", "image captioning"],
            "video_world": ["video generation", "world model", "Sora", "video understanding", "temporal modeling", "video prediction", "spatiotemporal"],
            "3d_spatial": ["3D reconstruction", "NeRF", "Gaussian splatting", "3D generation", "point cloud", "depth estimation", "3D vision", "spatial AI"],
            # 생성 모델
            "image_generation": ["diffusion model", "image generation", "text-to-image", "Stable Diffusion", "DALL-E", "image synthesis", "generative model"],
            "audio_speech": ["text-to-speech", "TTS", "speech recognition", "ASR", "audio generation", "voice synthesis", "speech synthesis", "audio LLM"],
            # 학습 & 최적화
            "reinforcement_learning": ["reinforcement learning", "RL", "RLHF", "policy optimization", "reward model", "PPO", "decision making", "offline RL"],
            "efficient_ai": ["model compression", "quantization", "pruning", "distillation", "efficient inference", "lightweight model", "edge AI", "PEFT", "LoRA"],
            # 응용 & 안전
            "robotics": ["robotics", "robot learning", "manipulation", "navigation", "embodied AI", "robot control", "autonomous robot"],
            "scientific_ai": ["AI for science", "AlphaFold", "protein structure", "drug discovery", "molecular generation", "scientific discovery", "chemistry AI"],
            "ai_safety": ["AI safety", "alignment", "RLHF", "red teaming", "jailbreak", "constitutional AI", "interpretability", "explainable AI", "fairness"],
        }

        results = {}
        all_papers = []
        global_exclude = set()  # 전체 중복 방지

        for field in fields:
            category = field_to_category.get(field, "Computer Vision")
            keywords = field_keywords.get(field, ["machine learning", "deep learning"])

            logger.info(f"[{field}] 검색 시작: {category} (목표: {count_per_field}개)")

            field_papers = []
            attempts = 0
            max_attempts = 3  # 최대 재시도 횟수

            while len(field_papers) < count_per_field and attempts < max_attempts:
                attempts += 1
                needed = count_per_field - len(field_papers)

                try:
                    # 검색 시도 (재시도 활성화)
                    papers = self.search(
                        category=category,
                        keywords=keywords,
                        count=needed + 2,  # 여유분 확보
                        source_count=3,  # 더 많은 소스 사용
                        exclude_titles=list(global_exclude),
                        retry_on_failure=True
                    )

                    # 중복 제거 및 추가
                    for paper in papers:
                        title = paper.get("title", "")
                        title_lower = title.lower()

                        if title and title_lower not in global_exclude:
                            paper["field"] = field
                            paper["field_name"] = category
                            field_papers.append(paper)
                            global_exclude.add(title_lower)

                            if len(field_papers) >= count_per_field:
                                break

                    if papers:
                        logger.info(f"[{field}] 시도 {attempts}: {len(papers)}개 검색, 현재 {len(field_papers)}/{count_per_field}개")

                except Exception as e:
                    logger.error(f"[{field}] 시도 {attempts} 실패: {e}")

                # API 레이트 리밋 방지
                if len(field_papers) < count_per_field:
                    time.sleep(1)

            # 결과 저장
            results[field] = field_papers[:count_per_field]
            all_papers.extend(results[field])

            if len(results[field]) < count_per_field:
                logger.warning(f"[{field}] 목표 {count_per_field}개 중 {len(results[field])}개만 검색됨")
            else:
                logger.info(f"[{field}] 완료: {len(results[field])}개 검색")

            # 분야 간 대기
            time.sleep(0.5)

        # papers.json에 저장
        if all_papers:
            self._save_to_papers_json(all_papers)
            logger.info(f"총 {len(all_papers)}개 논문 검색 완료")

        return results

    def _save_to_papers_json(self, papers: List[Dict]) -> None:
        """검색된 논문을 papers.json에 저장"""
        papers_file = PROJECT_ROOT / "data" / "papers.json"

        try:
            # 기존 데이터 로드
            existing_papers = []
            if papers_file.exists():
                with open(papers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        existing_papers = data
                    elif isinstance(data, dict) and "papers" in data:
                        existing_papers = data.get("papers", [])

            # 기존 논문 제목 집합 (중복 체크용)
            existing_titles = {p.get("title", "").lower() for p in existing_papers if p.get("title")}

            # 새 논문 추가 (중복 제외)
            added_count = 0
            for paper in papers:
                title = paper.get("title", "")
                if title and title.lower() not in existing_titles:
                    # papers.json 형식에 맞게 변환
                    paper_entry = {
                        "title": title,
                        "year": paper.get("year", datetime.now().year),
                        "authors": paper.get("authors", []),
                        "arxiv_id": paper.get("arxiv_id", ""),
                        "url": paper.get("url", ""),
                        "pdf_url": paper.get("pdf_url", ""),
                        "abstract": paper.get("abstract", ""),
                        "source": paper.get("source", ""),
                        "field": paper.get("field", ""),
                        "citations": paper.get("citations", 0),
                        "added_at": datetime.now().isoformat(),
                        "status": "pending",  # 리뷰 생성 대기
                    }
                    existing_papers.insert(0, paper_entry)  # 최신 논문을 앞에 추가
                    existing_titles.add(title.lower())
                    added_count += 1

            # 저장
            papers_file.parent.mkdir(parents=True, exist_ok=True)
            with open(papers_file, 'w', encoding='utf-8') as f:
                json.dump(existing_papers, f, ensure_ascii=False, indent=2)

            logger.info(f"papers.json에 {added_count}개 논문 추가 (총 {len(existing_papers)}개)")

        except Exception as e:
            logger.error(f"papers.json 저장 실패: {e}")
