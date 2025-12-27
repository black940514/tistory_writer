"""
OpenAI API 클라이언트
"""
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    OpenAI API 클라이언트
    
    논문 리스트 생성 및 논문 리뷰 생성을 담당합니다.
    프롬프트는 외부 YAML 파일에서 로드하여 커스터마이징 가능합니다.
    
    """
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", prompts_file: str = "prompts.yaml"):
        """
        OpenAI 클라이언트 초기화
        
        Args:
            api_key: OpenAI API 키
            model: 사용할 모델 (기본값: gpt-4o-mini)
                  - gpt-4o-mini: 빠르고 저렴한 모델 (권장)
                  - gpt-4o: 더 강력한 모델
                  - gpt-5.2: 최신 모델 (max_completion_tokens 사용)
            prompts_file: 프롬프트 설정 파일 경로
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
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
        return template.format(**kwargs)
    
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
            
            completion_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert in academic paper analysis. Generate a list of paper titles only. You MUST respond with valid JSON format containing a 'titles' array of strings."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            if "gpt-4" in self.model.lower() or "gpt-3.5" in self.model.lower():
                completion_params["response_format"] = {"type": "json_object"}
            
            # 제목만이므로 토큰 수 계산: 제목 하나당 평균 100토큰, 200개면 20000토큰 필요
            if "gpt-5" in self.model.lower() or "o1" in self.model.lower():
                completion_params["max_completion_tokens"] = 8000  # 충분히 크게
            else:
                completion_params["max_tokens"] = 6000
            
            response = self.client.chat.completions.create(**completion_params)
            
            import json
            import re
            
            # 응답 확인
            if not response.choices or not response.choices[0].message:
                raise ValueError("OpenAI API 응답에 choices가 없습니다.")
            
            response_content = response.choices[0].message.content
            
            if not response_content or not response_content.strip():
                raise ValueError("OpenAI API 응답이 비어있습니다.")
            
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
        paper_titles: List[str]
    ) -> List[Dict]:
        """
        논문 제목 리스트를 받아서 상세 정보 생성 (2단계)
        
        Args:
            paper_titles: 1단계에서 받은 논문 제목 리스트 (문자열 리스트)
        
        Returns:
            상세 정보가 포함된 논문 리스트 (title, authors, year, citations, importance_score, url, abstract)
        """
        try:
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
- abstract: 논문 초록 요약 (간략하게, 없으면 null)

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
      "abstract": "논문 초록 요약"
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
            
            completion_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert in academic paper analysis. Add detailed information (arxiv_id, url, abstract) to the given paper list. You MUST respond with valid JSON format containing a 'papers' array."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7
            }
            
            if "gpt-4" in self.model.lower() or "gpt-3.5" in self.model.lower():
                completion_params["response_format"] = {"type": "json_object"}
            
            # 상세 정보이므로 더 많은 토큰 필요
            if "gpt-5" in self.model.lower() or "o1" in self.model.lower():
                completion_params["max_completion_tokens"] = 4000
            else:
                completion_params["max_tokens"] = 3000
            
            response = self.client.chat.completions.create(**completion_params)
            
            import json
            import re
            
            # 응답 확인
            if not response.choices or not response.choices[0].message:
                raise ValueError("OpenAI API 응답에 choices가 없습니다.")
            
            response_content = response.choices[0].message.content
            
            if not response_content or not response_content.strip():
                logger.error(f"OpenAI API 응답이 비어있습니다. 전체 응답: {response}")
                raise ValueError("OpenAI API 응답이 비어있습니다.")
            
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
    
    def generate_paper_list(
        self,
        topic: str = "AI/ML",
        count: int = 100,
        recent_years: int = 5,
        exclude_titles: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        OpenAI를 사용하여 중요 논문 리스트 생성 (기존 메서드, 호환성 유지)
        
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
            
            # gpt-5.2 같은 새 모델은 max_completion_tokens 사용
            completion_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are an expert in academic paper analysis. Generate a comprehensive list of papers based on Google Scholar data. The list doesn't need to be perfectly accurate - include representative papers from the field. You MUST respond with valid JSON format containing a 'papers' array."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }
            
            # JSON 응답 형식 지원 (일부 모델만 지원)
            # gpt-5.2는 response_format을 지원하지 않을 수 있으므로 프롬프트에서 강조
            if "gpt-4" in self.model.lower() or "gpt-3.5" in self.model.lower():
                completion_params["response_format"] = {"type": "json_object"}
            
            # 모델에 따라 토큰 제한 설정 (10개 논문 기준으로 충분한 토큰)
            if "gpt-5" in self.model.lower() or "o1" in self.model.lower():
                completion_params["max_completion_tokens"] = 4000  # 10개 논문에 충분
            else:
                completion_params["max_tokens"] = 3000  # 10개 논문에 충분
            
            response = self.client.chat.completions.create(**completion_params)
            
            import json
            import re
            
            # 응답 확인
            if not response.choices or not response.choices[0].message:
                raise ValueError("OpenAI API 응답에 choices가 없습니다.")
            
            response_content = response.choices[0].message.content
            
            if not response_content or not response_content.strip():
                logger.error(f"OpenAI API 응답이 비어있습니다. 전체 응답: {response}")
                raise ValueError("OpenAI API 응답이 비어있습니다.")
            
            logger.debug(f"OpenAI 응답 길이: {len(response_content)} bytes")
            logger.debug(f"OpenAI 응답 시작 부분: {response_content[:200]}")
            
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
        model: Optional[str] = None
    ) -> str:
        """
        논문 리뷰 생성
        
        Args:
            paper: 논문 정보 딕셔너리
            language: 출력 언어 (ko, en)
            model: 사용할 모델 (None이면 self.model 사용)
        
        Returns:
            생성된 논문 리뷰 (마크다운 형식)
        """
        try:
            # 모델 지정 (없으면 기본 모델 사용)
            review_model = model if model else self.model
            # 프롬프트 템플릿에서 로드
            prompt_template = self.prompts.get('paper_review_prompt', '')
            if not prompt_template:
                prompt_template = "다음 논문에 대한 상세한 리뷰를 작성해주세요:\n\n{paper_info}"
            
            # 논문 정보 추출
            title = paper.get('title', 'N/A')
            authors = ', '.join(paper.get('authors', [])[:3]) if isinstance(paper.get('authors'), list) else str(paper.get('authors', 'N/A'))
            year = paper.get('year', 'N/A')
            citations = paper.get('citations', 'N/A')
            abstract = paper.get('abstract', 'N/A')
            
            # 프롬프트 템플릿에 개별 변수 전달
            prompt = self._format_prompt(
                prompt_template,
                title=title,
                authors=authors,
                year=year,
                citations=citations,
                abstract=abstract
            )
            
            # gpt-5.2 같은 새 모델은 max_completion_tokens 사용, 기존 모델은 max_tokens 사용
            completion_params = {
                "model": review_model,
                "messages": [
                    {"role": "system", "content": "You are a junior AI engineer writing blog posts for learning and study purposes. Write in a natural, column-style format without numbered lists or overly structured sections. Focus on problem definition and its significance. Use past tense declarative style (했다체) in Korean, ending sentences with forms like '했다', '제시했다', '설명했다'."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }
            
            if "gpt-5" in review_model.lower() or "o1" in review_model.lower():
                completion_params["max_completion_tokens"] = 8000
            else:
                completion_params["max_tokens"] = 4000
            
            response = self.client.chat.completions.create(**completion_params)
            
            review = response.choices[0].message.content
            logger.info("논문 리뷰 생성 완료")
            
            return review
            
        except Exception as e:
            logger.error(f"논문 리뷰 생성 오류: {e}", exc_info=True)
            raise
