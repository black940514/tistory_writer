"""
Claude API 클라이언트
"""
import logging
import random
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Literal
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Scientific MCP 클라이언트 (옵션)
try:
    from .scientific_mcp_client import ScientificMCPClient, create_scientific_client
    SCIENTIFIC_MCP_AVAILABLE = True
except ImportError:
    SCIENTIFIC_MCP_AVAILABLE = False
    logger.debug("Scientific MCP 클라이언트를 로드할 수 없습니다. httpx 패키지가 필요합니다.")


class ClaudeClient:
    """
    Claude API 클라이언트

    논문 리스트 생성 및 논문 리뷰 생성을 담당합니다.
    프롬프트는 외부 YAML 파일에서 로드하여 커스터마이징 가능합니다.

    """
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        search_model: str = "claude-3-5-haiku-20241022",
        prompts_file: str = "prompts.yaml"
    ):
        """
        Claude 클라이언트 초기화

        Args:
            api_key: Anthropic API 키
            model: 기본 모델 (기본값: claude-sonnet-4-20250514)
            search_model: 논문 검색/리스트 생성용 모델 (기본값: claude-3-5-haiku-20241022)
                  - 논문 검색, 코멘트 생성 등 간단한 작업에 사용
                  - 빠르고 저렴한 haiku 모델 권장
            prompts_file: 프롬프트 설정 파일 경로
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.search_model = search_model  # 검색용 모델 (haiku)
        self.prompts = self._load_prompts(prompts_file)

    def _load_prompts(self, prompts_file: str) -> Dict:
        """프롬프트 파일 로드"""
        try:
            prompts_path = Path(prompts_file)
            if not prompts_path.is_absolute():
                # 상대 경로인 경우 현재 작업 디렉토리에서 찾기
                prompts_path = Path.cwd() / prompts_file

            if prompts_path.exists():
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    prompts = yaml.safe_load(f)
                    logger.info(f"프롬프트 파일 로드 완료: {prompts_file}")
                return prompts or {}
            else:
                logger.warning(f"프롬프트 파일을 찾을 수 없습니다: {prompts_file}")
                return {}
        except Exception as e:
            logger.error(f"프롬프트 파일 로드 오류: {e}")
            return {}

    def _format_prompt(self, template: str, **kwargs) -> str:
        """프롬프트 템플릿 포맷팅"""
        # 중괄호 이스케이프 처리: {{ }} -> { }, {var} -> 치환
        # Python format에서 {{ }}는 리터럴 중괄호로 해석됨
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # 누락된 키가 있으면 기본값으로 대체
            logger.warning(f"프롬프트 템플릿에 누락된 키가 있습니다: {e}. 기본값으로 대체합니다.")
            # 누락된 키를 찾아서 기본값으로 대체
            import re
            missing_keys = set(re.findall(r'\{(\w+)\}', template)) - set(kwargs.keys())
            for key in missing_keys:
                template = template.replace(f'{{{key}}}', 'N/A')
            return template.format(**kwargs)

    def generate_paper_comment(
        self,
        title: str,
        abstract: str,
        field: str = "",
        max_tokens: int = 50
    ) -> str:
        """
        논문에 대한 간단한 AI 코멘트 생성

        Args:
            title: 논문 제목
            abstract: 논문 초록
            field: 논문 분야 (선택)
            max_tokens: 최대 토큰 수

        Returns:
            1-2문장의 간단한 코멘트
        """
        try:
            prompt = f"""논문의 핵심 목적을 20글자 이내 한국어로 작성.

제목: {title}
초록: {abstract[:300] if abstract else '없음'}

[규칙]
- 20글자 이내 (엄격히)
- "이 논문은", "본 연구는" 등 서두 금지
- 핵심 동작/목적만 (예: "LLM 추론 속도 3배 향상", "이미지 생성 품질 개선")
- 이모지 사용 금지

코멘트:"""

            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # 빠른 응답을 위해 Haiku 사용
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            comment = response.content[0].text.strip()
            # 앞뒤 따옴표 제거
            if comment.startswith('"') and comment.endswith('"'):
                comment = comment[1:-1]
            if comment.startswith("'") and comment.endswith("'"):
                comment = comment[1:-1]

            logger.info(f"논문 코멘트 생성 완료: {title[:30]}...")
            return comment

        except Exception as e:
            logger.error(f"코멘트 생성 실패: {e}")
            return ""

    def generate_paper_comments_batch(
        self,
        papers: List[Dict],
        max_papers: int = 10
    ) -> Dict[str, str]:
        """
        여러 논문에 대한 코멘트 일괄 생성

        Args:
            papers: 논문 리스트 (title, abstract, field 포함)
            max_papers: 한 번에 처리할 최대 논문 수

        Returns:
            {논문제목: 코멘트} 딕셔너리
        """
        comments = {}
        papers_to_process = papers[:max_papers]

        for paper in papers_to_process:
            title = paper.get('title', '')
            if not title:
                continue

            comment = self.generate_paper_comment(
                title=title,
                abstract=paper.get('abstract', ''),
                field=paper.get('field', '')
            )
            if comment:
                comments[title] = comment

        logger.info(f"{len(comments)}개 논문 코멘트 생성 완료")
        return comments

    def generate_paper_list_titles_only(
        self,
        topic: str = "AI/ML",
        count: int = 100,
        recent_years: int = 5,
        exclude_titles: Optional[List[str]] = None
    ) -> List[str]:
        """
        논문 제목 리스트만 생성 (1단계: 제목만)

        Args:
            topic: 주제
            count: 논문 개수
            recent_years: 최근 몇 년간의 논문만 선택
            exclude_titles: 제외할 논문 제목 리스트

        Returns:
            논문 제목 리스트 (문자열 리스트)
        """
        try:
            prompt_template = self.prompts.get('paper_list_titles_prompt', '')
            if not prompt_template:
                # 기본 프롬프트
                prompt_template = """Google Scholar 기준으로 {recent_years}년간 {topic} 분야의 주요 논문 {count}개의 제목만 JSON 형식으로 정리해주세요.

제목만 포함하고, 다른 정보는 포함하지 마세요.

반드시 다음 JSON 형식으로 응답해주세요:
{{
  "titles": [
    "논문 제목 1",
    "논문 제목 2",
    "논문 제목 3",
    ...
  ]
}}

정확히 {count}개의 논문 제목을 반환해주세요."""

            exclude_text = ""
            if exclude_titles:
                exclude_text = f"\n\n중요: 다음 논문들은 이미 수집되었으므로 제외하고 새로운 논문만 제시해주세요:\n"
                for title in exclude_titles[:100]:  # 제목만이므로 더 많이
                    exclude_text += f"- {title}\n"

            prompt = self._format_prompt(
                prompt_template,
                topic=topic,
                count=count,
                recent_years=recent_years
            ) + exclude_text

            response = self.client.messages.create(
                model=self.search_model,  # 검색용 모델 (haiku)
                max_tokens=8000,
                system="You are an expert in academic paper analysis. Generate a list of paper titles only. You MUST respond with valid JSON format containing a 'titles' array of strings.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            import json
            import re

            # 응답 확인
            if not response.content:
                raise ValueError("Claude API 응답이 비어있습니다.")

            response_content = response.content[0].text

            if not response_content or not response_content.strip():
                raise ValueError("Claude API 응답이 비어있습니다.")

            logger.debug(f"논문 제목 리스트 응답 길이: {len(response_content)} bytes")
            logger.debug(f"논문 제목 리스트 응답 시작 부분: {response_content[:200]}")

            try:
                result = json.loads(response_content)
                titles = result.get('titles', [])

                if not titles:
                    # 하위 호환성: 'papers' 키 확인
                    if 'papers' in result:
                        titles = [p.get('title', '') if isinstance(p, dict) else str(p) for p in result['papers']]
                    elif isinstance(result, list):
                        titles = [str(t) for t in result]
                    logger.warning(f"논문 제목 리스트가 0개입니다. 응답 구조: {list(result.keys()) if isinstance(result, dict) else 'list'}")

                # 문자열로 변환 및 필터링
                titles = [str(t).strip() for t in titles if t]

                logger.info(f"{len(titles)}개의 논문 제목 리스트 생성 완료")
                return titles
            except json.JSONDecodeError as e:
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        titles = result.get('titles', [])
                        if not titles and 'papers' in result:
                            # 하위 호환성
                            titles = [p.get('title', '') if isinstance(p, dict) else str(p) for p in result['papers']]
                        titles = [str(t).strip() for t in titles if t]
                        logger.info(f"코드 블록에서 JSON 추출 성공: {len(titles)}개 논문 제목")
                        return titles
                    except:
                        pass
                logger.error(f"JSON 파싱 오류: {e}")
                logger.error(f"응답 내용: {response_content[:1000]}")
                raise

        except Exception as e:
            logger.error(f"논문 제목 리스트 생성 오류: {e}", exc_info=True)
            raise

    def generate_paper_details(
        self,
        paper_titles: List[str],
        is_category_search: bool = False,
        count: int = 5
    ) -> List[Dict]:
        """
        논문 제목 리스트를 받아서 상세 정보 생성 (2단계)

        Args:
            paper_titles: 1단계에서 받은 논문 제목 리스트 (문자열 리스트)
            is_category_search: 분야별 최신 논문 검색 모드
            count: 검색할 논문 개수 (is_category_search=True일 때만 사용)

        Returns:
            상세 정보가 포함된 논문 리스트 (title, authors, year, citations, importance_score, url, abstract)
        """
        try:
            # 분야별 최신 논문 검색 모드
            if is_category_search:
                return self._search_latest_papers_by_query(paper_titles[0], count)

            prompt_template = self.prompts.get('paper_details_prompt', '')
            if not prompt_template:
                prompt_template = """다음 논문 제목들의 상세 정보를 제공해주세요:

{papers_list}

각 논문에 대해 다음 정보를 포함해주세요:
- title: 논문 제목 (필수)
- authors: 저자 목록 배열 (최대 3명, 필수)
- year: 발행년도 (필수)
- citations: 인용수 (대략적 추정치, 숫자)
- importance_score: 중요도 점수 1-100 (대략적 추정치, 숫자)
- url: 논문 URL 또는 arXiv 링크 (있으면, 없으면 null)
- abstract: 논문 초록 (상세하게 작성 - 해결하려는 문제, 제안 방법, 핵심 기여, 주요 실험 결과 포함. 최소 150자 이상)

반드시 다음 JSON 형식으로 응답해주세요:
{{
  "papers": [
    {{
      "title": "논문 제목",
      "authors": ["저자1", "저자2", "저자3"],
      "year": 2024,
      "citations": 1000,
      "importance_score": 90,
      "url": "https://arxiv.org/abs/2301.00001",
      "abstract": "이 논문은 ... 문제를 해결하기 위해 ... 방법을 제안한다. 핵심 기여는 ... 이며, 실험 결과 ... 를 달성했다."
    }},
    ...
  ]
}}"""

            # 논문 제목 리스트를 텍스트로 변환
            papers_text = ""
            for i, title in enumerate(paper_titles, 1):
                papers_text += f"{i}. {title}\n"

            prompt = self._format_prompt(
                prompt_template,
                papers_list=papers_text
            )

            response = self.client.messages.create(
                model=self.search_model,  # 검색용 모델 (haiku)
                max_tokens=4000,
                system="You are an expert in academic paper analysis. Add detailed information (arxiv_id, url, abstract) to the given paper list. You MUST respond with valid JSON format containing a 'papers' array.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            import json
            import re

            # 응답 확인
            if not response.content:
                raise ValueError("Claude API 응답이 비어있습니다.")

            response_content = response.content[0].text

            if not response_content or not response_content.strip():
                logger.error(f"Claude API 응답이 비어있습니다. 전체 응답: {response}")
                raise ValueError("Claude API 응답이 비어있습니다.")

            logger.debug(f"논문 상세 정보 응답 길이: {len(response_content)} bytes")
            logger.debug(f"논문 상세 정보 응답 시작 부분: {response_content[:200]}")

            try:
                result = json.loads(response_content)
                papers = result.get('papers', [])

                if not papers:
                    if 'papers' not in result and isinstance(result, list):
                        papers = result
                    logger.warning(f"논문 상세 정보가 0개입니다.")

                logger.info(f"{len(papers)}개의 논문 상세 정보 생성 완료")
                return papers
            except json.JSONDecodeError as e:
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        papers = result.get('papers', [])
                        logger.info(f"코드 블록에서 JSON 추출 성공: {len(papers)}개 논문")
                        return papers
                    except:
                        pass
                logger.error(f"JSON 파싱 오류: {e}")
                logger.error(f"응답 내용: {response_content[:1000]}")
                raise

        except Exception as e:
            logger.error(f"논문 상세 정보 생성 오류: {e}", exc_info=True)
            raise

    def _search_latest_papers_by_query(self, query: str, count: int = 5) -> List[Dict]:
        """
        분야별 최신 논문 검색

        Args:
            query: 검색 쿼리 (분야명 + 키워드 포함)
            count: 검색할 논문 개수

        Returns:
            최신 논문 리스트
        """
        import json
        import re

        prompt = f"""당신은 AI/ML 논문 전문가입니다. 다음 분야의 최신 중요 논문 {count}개를 찾아주세요:

검색 분야: {query}

요구사항:
1. 2024년 또는 2025년에 발표된 최신 논문 위주로 선정
2. 영향력이 크고 인용이 많은 논문 우선
3. 실제 존재하는 논문만 포함 (가상의 논문 금지)
4. arXiv, NeurIPS, ICML, CVPR, ACL 등 주요 학회/저널 논문

반드시 다음 JSON 형식으로 응답해주세요:
{{
  "papers": [
    {{
      "title": "실제 논문 제목",
      "authors": ["저자1", "저자2"],
      "year": 2024,
      "citations": 100,
      "importance_score": 85,
      "url": "https://arxiv.org/abs/xxxx.xxxxx",
      "abstract": "이 논문은 ... 문제를 해결하기 위해 ... 방법을 제안한다."
    }}
  ]
}}"""

        try:
            response = self.client.messages.create(
                model=self.search_model,  # 검색용 모델 (haiku)
                max_tokens=4000,
                system="You are an expert in AI/ML research. Find real, recently published papers. Always respond with valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            if not response.content:
                return []

            response_content = response.content[0].text

            try:
                result = json.loads(response_content)
                papers = result.get('papers', [])
                logger.info(f"분야별 최신 논문 {len(papers)}개 검색 완료")
                return papers
            except json.JSONDecodeError:
                # JSON 코드 블록에서 추출 시도
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                    return result.get('papers', [])
                return []

        except Exception as e:
            logger.error(f"분야별 최신 논문 검색 오류: {e}")
            return []

    def generate_paper_list(
        self,
        topic: str = "AI/ML",
        count: int = 100,
        recent_years: int = 5,
        exclude_titles: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Claude를 사용하여 중요 논문 리스트 생성 (기존 메서드, 호환성 유지)

        Args:
            topic: 주제 (예: "AI/ML", "Large Language Models", "Computer Vision")
            count: 논문 개수
            recent_years: 최근 몇 년간의 논문만 선택
            exclude_titles: 제외할 논문 제목 리스트 (중복 방지용)

        Returns:
            논문 리스트 (중요도 및 인용수 기준으로 정렬됨)
        """
        try:
            # 프롬프트 템플릿에서 로드
            prompt_template = self.prompts.get('paper_list_prompt', '')

            # 제외할 논문 목록이 있으면 프롬프트에 추가
            exclude_text = ""
            if exclude_titles:
                exclude_text = f"\n\n중요: 다음 논문들은 이미 수집되었으므로 제외하고 새로운 논문만 제시해주세요:\n"
                for title in exclude_titles[:50]:  # 너무 많으면 처음 50개만
                    exclude_text += f"- {title}\n"

            prompt = self._format_prompt(
                prompt_template,
                topic=topic,
                count=count,
                recent_years=recent_years
            ) + exclude_text

            response = self.client.messages.create(
                model=self.search_model,  # 검색용 모델 사용 (haiku)
                max_tokens=4000,
                system="You are an expert in academic paper analysis. Generate a comprehensive list of papers based on Google Scholar data. The list doesn't need to be perfectly accurate - include representative papers from the field. You MUST respond with valid JSON format containing a 'papers' array.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            import json
            import re

            # 응답 확인
            if not response.content:
                raise ValueError("Claude API 응답이 비어있습니다.")

            response_content = response.content[0].text

            if not response_content or not response_content.strip():
                logger.error(f"Claude API 응답이 비어있습니다. 전체 응답: {response}")
                raise ValueError("Claude API 응답이 비어있습니다.")

            logger.debug(f"Claude 응답 길이: {len(response_content)} bytes")
            logger.debug(f"Claude 응답 시작 부분: {response_content[:200]}")

            try:
                # JSON 파싱 시도
                result = json.loads(response_content)
                papers = result.get('papers', [])

                if not papers:
                    logger.warning(f"논문이 0개입니다. 응답 구조 확인: {list(result.keys())}")
                    logger.warning(f"응답 내용 일부: {response_content[:1000]}")
                    # papers 키가 없으면 전체를 papers로 시도
                    if 'papers' not in result and isinstance(result, list):
                        papers = result
                        logger.info("응답이 배열 형식입니다. papers 배열로 사용합니다.")
                    elif isinstance(result, dict) and len(result) > 0:
                        # 다른 키가 있을 수 있으므로 첫 번째 키 확인
                        first_key = list(result.keys())[0]
                        logger.warning(f"응답의 첫 번째 키: {first_key}")

                logger.info(f"{len(papers)}개의 논문 리스트 생성 완료")
                return papers
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {e}")
                logger.error(f"응답 내용 처음 2000자: {response_content[:2000]}")
                # 마크다운 코드 블록에서 JSON 추출 시도
                json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', response_content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        papers = result.get('papers', [])
                        logger.info(f"코드 블록에서 JSON 추출 성공: {len(papers)}개 논문")
                        return papers
                    except:
                        pass
                raise

        except Exception as e:
            logger.error(f"논문 리스트 생성 오류: {e}", exc_info=True)
            raise

    def generate_paper_review(
        self,
        paper: Dict,
        language: str = "ko",
        model: Optional[str] = None,
        use_scientific_skills: bool = False,
        scientific_style: Literal["peer-review", "literature-review", "scientific-critical-thinking", "scientific-writing"] = "peer-review"
    ) -> str:
        """
        논문 리뷰 생성

        Args:
            paper: 논문 정보 딕셔너리
            language: 출력 언어 (ko, en)
            model: 사용할 모델 (None이면 self.model 사용)
            use_scientific_skills: Scientific Skills 보조 가이드 사용 여부
                - True: prompts.yaml + Scientific Skills 보조 가이드 결합
                - False: prompts.yaml만 사용 (기본값)
            scientific_style: Scientific Skills 보조 가이드 스타일
                - "peer-review": 학술 피어 리뷰 관점 (기본값)
                - "literature-review": 문헌 리뷰 관점
                - "scientific-critical-thinking": 비판적 분석 관점
                - "scientific-writing": 커뮤니케이션 관점

        Returns:
            생성된 논문 리뷰 (마크다운 형식)
        """
        # Scientific Skills 보조 가이드 가져오기
        skill_supplement = ""
        if use_scientific_skills and SCIENTIFIC_MCP_AVAILABLE:
            try:
                client = create_scientific_client()
                skill_supplement = client.get_skill_supplement(scientific_style)
                logger.info(f"Scientific Skills 보조 가이드 적용: {scientific_style}")
            except Exception as e:
                logger.warning(f"Scientific Skills 보조 가이드 로드 실패: {e}")

        try:
            # 모델 지정 (없으면 기본 모델 사용)
            review_model = model if model else self.model

            # 프롬프트 리스트에서 랜덤 선택
            prompts_list = self.prompts.get('paper_review_prompts', [])
            if prompts_list:
                selected = random.choice(prompts_list)
                prompt_template = selected.get('prompt', '')
                style_name = selected.get('name', 'unknown')
                logger.info(f"프롬프트 스타일 선택: {style_name}")
            else:
                # 하위 호환성 (paper_review_prompts가 없으면 paper_review_prompt 사용)
                prompt_template = self.prompts.get('paper_review_prompt', '')

            if not prompt_template:
                # 기본 템플릿 (개별 변수 사용)
                prompt_template = """다음 논문에 대한 상세한 리뷰를 작성해주세요:

[논문 정보]
- 제목: {title}
- 저자: {authors}
- 발행년도: {year}
- 인용수: {citations}
- 초록: {abstract}
- 논문 링크: {url}

위 논문에 대해 기술 블로그 스타일의 상세한 리뷰를 한국어로 작성해주세요."""

            # 논문 정보 추출
            title = paper.get('title', 'N/A')
            authors = ', '.join(paper.get('authors', [])[:3]) if isinstance(paper.get('authors'), list) else str(paper.get('authors', 'N/A'))
            year = paper.get('year', 'N/A')
            citations = paper.get('citations', 'N/A')
            abstract = paper.get('abstract', 'N/A')
            url = paper.get('url', 'N/A')

            # 프롬프트 템플릿에 개별 변수 전달
            prompt = self._format_prompt(
                prompt_template,
                title=title,
                authors=authors,
                year=year,
                citations=citations,
                abstract=abstract,
                url=url
            )

            # Scientific Skills 보조 가이드가 있으면 프롬프트 끝에 추가
            if skill_supplement:
                prompt = f"""{prompt}

---

{skill_supplement}

위 체크포인트들을 리뷰에 자연스럽게 반영해주세요."""

            response = self.client.messages.create(
                model=review_model,
                max_tokens=8000,
                system="You are a junior AI engineer writing blog posts for learning and study purposes. Write in a natural, column-style format without numbered lists or overly structured sections. Focus on problem definition and its significance. Use past tense declarative style (했다체) in Korean, ending sentences with forms like '했다', '제시했다', '설명했다'.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            if not response.content:
                raise ValueError("Claude API 응답이 비어있습니다.")

            review = response.content[0].text
            logger.info("논문 리뷰 생성 완료")

            return review

        except Exception as e:
            logger.error(f"논문 리뷰 생성 오류: {e}", exc_info=True)
            raise

    def _get_scientific_supplement(self, style: str = "peer-review") -> str:
        """
        Scientific Skills 보조 가이드 가져오기

        Args:
            style: 리뷰 스타일

        Returns:
            보조 가이드 텍스트 (실패 시 빈 문자열)
        """
        if not SCIENTIFIC_MCP_AVAILABLE:
            return ""

        try:
            client = create_scientific_client()
            return client.get_skill_supplement(style)
        except Exception as e:
            logger.warning(f"Scientific Skills 보조 가이드 로드 실패: {e}")
            return ""

    def generate_scientific_paper_review(
        self,
        paper: Dict,
        style: str = "peer-review",
        language: str = "ko",
        model: Optional[str] = None
    ) -> str:
        """
        Scientific Skills 보조 가이드를 사용한 논문 리뷰 생성

        prompts.yaml의 메인 프롬프트 + Scientific Skills 보조 가이드를 결합하여
        더 전문적인 리뷰를 생성합니다.

        Args:
            paper: 논문 정보 딕셔너리 (title, authors, year, abstract, url 등)
            style: Scientific Skills 보조 가이드 스타일
                - "peer-review": 학술 피어 리뷰 관점 (기본값)
                - "literature-review": 문헌 리뷰 관점
                - "scientific-critical-thinking": 비판적 분석 관점
                - "scientific-writing": 커뮤니케이션 관점
            language: 출력 언어 (ko/en)
            model: 사용할 모델 (None이면 self.model 사용)

        Returns:
            생성된 논문 리뷰 (마크다운 형식)

        Example:
            >>> client = ClaudeClient(api_key="...")
            >>> paper = {"title": "Attention Is All You Need", "authors": [...], ...}
            >>> review = client.generate_scientific_paper_review(paper, style="peer-review")
        """
        # generate_paper_review를 호출하되 Scientific Skills를 활성화
        return self.generate_paper_review(
            paper=paper,
            language=language,
            model=model,
            use_scientific_skills=True,
            scientific_style=style
        )
