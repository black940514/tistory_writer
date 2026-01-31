"""
Scientific Skills MCP 클라이언트

claude-scientific-skills MCP 서버를 통해 전문적인 논문 리뷰를 생성합니다.
https://github.com/K-Dense-AI/claude-scientific-skills

MCP 서버에서 스킬 가이드 문서를 로드하고, Claude API를 통해 리뷰를 생성합니다.
"""
import asyncio
import logging
from typing import Dict, Optional, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScientificSkillConfig:
    """Scientific Skills 설정"""
    server_url: str = "https://mcp.k-dense.ai/claude-scientific-skills/mcp"
    timeout: float = 120.0
    sse_read_timeout: float = 300.0


class ScientificMCPClient:
    """
    Scientific Skills MCP 클라이언트

    MCP 서버에서 스킬 가이드 문서를 로드하고,
    해당 가이드를 기반으로 Claude API를 통해 전문적인 논문 리뷰를 생성합니다.

    지원 스킬:
    - peer-review: 학술 논문 피어 리뷰 스타일
    - literature-review: 문헌 리뷰 스타일
    - scientific-writing: 과학적 글쓰기 스타일
    - scientific-critical-thinking: 비판적 분석 스타일
    """

    REVIEW_SKILLS = {
        "peer-review": "학술 피어 리뷰 (방법론, 결과, 결론 평가)",
        "literature-review": "문헌 리뷰 (관련 연구 맥락, 기여도 분석)",
        "scientific-critical-thinking": "비판적 분석 (가정, 논리, 증거 검토)",
        "scientific-writing": "과학적 글쓰기 (명확성, 구조, 설득력)"
    }

    # Scientific Skills 보조 가이드 (prompts.yaml과 함께 사용)
    # MCP 서버에서 가져온 스킬 문서를 보완하는 간결한 가이드
    SKILL_SUPPLEMENTS = {
        "peer-review": """[학술 피어 리뷰 관점 - 추가 체크포인트]

리뷰 작성 시 다음 학술적 관점을 반영해주세요:

1. **방법론 검증**: 실험 설계가 주장을 뒷받침하기에 충분한가?
2. **재현성 평가**: 논문 정보만으로 재현이 가능한가?
3. **통계적 타당성**: 결과의 통계적 유의성이 적절히 보고되었는가?
4. **비교 공정성**: baseline 선정과 비교 방식이 공정한가?
5. **한계 인정**: 저자가 한계점을 솔직하게 인정했는가?""",

        "literature-review": """[문헌 리뷰 관점 - 추가 체크포인트]

리뷰 작성 시 다음 맥락적 관점을 반영해주세요:

1. **연구 계보**: 이 논문이 어떤 연구 흐름에 속하는가?
2. **선행 연구 위치**: 주요 선행 연구들과 어떻게 연결되는가?
3. **기여의 참신성**: 진정으로 새로운 기여는 무엇인가?
4. **영향력 예측**: 향후 연구에 어떤 영향을 미칠 것인가?
5. **실무 적용성**: 산업 현장에서의 활용 가능성은?""",

        "scientific-critical-thinking": """[비판적 사고 관점 - 추가 체크포인트]

리뷰 작성 시 다음 비판적 관점을 반영해주세요:

1. **가정 검토**: 논문의 핵심 가정들이 현실적인가?
2. **논리 검증**: 전제에서 결론까지의 논리가 타당한가?
3. **대안 가설**: 같은 결과를 설명할 다른 가설은 없는가?
4. **일반화 한계**: 결과를 어디까지 일반화할 수 있는가?
5. **누락된 실험**: 주장을 강화하려면 어떤 추가 실험이 필요한가?""",

        "scientific-writing": """[과학적 글쓰기 관점 - 추가 체크포인트]

리뷰 작성 시 다음 커뮤니케이션 관점을 반영해주세요:

1. **핵심 메시지**: 독자가 기억해야 할 한 문장은?
2. **직관적 설명**: 비전공자도 핵심을 이해할 수 있는가?
3. **시각적 구조**: 글의 흐름이 자연스럽고 읽기 쉬운가?
4. **실용적 통찰**: 실무자에게 도움이 되는 정보가 있는가?
5. **후속 학습**: 더 깊이 공부하고 싶은 사람을 위한 방향은?"""
    }

    def __init__(self, config: Optional[ScientificSkillConfig] = None):
        self.config = config or ScientificSkillConfig()
        self._skill_docs_cache: Dict[str, str] = {}

    def list_available_skills(self) -> Dict[str, str]:
        """사용 가능한 리뷰 스킬 목록 반환"""
        return self.REVIEW_SKILLS.copy()

    def _format_paper_info(self, paper_info: Dict[str, Any]) -> str:
        """논문 정보를 포맷팅된 텍스트로 변환"""
        title = paper_info.get('title', 'N/A')
        authors = paper_info.get('authors', [])
        if isinstance(authors, list):
            authors = ', '.join(authors[:5])
        year = paper_info.get('year', 'N/A')
        citations = paper_info.get('citations', 'N/A')
        abstract = paper_info.get('abstract', 'N/A')
        url = paper_info.get('url', 'N/A')

        return f"""[논문 정보]
제목: {title}
저자: {authors}
발행년도: {year}
인용수: {citations}
논문 링크: {url}

[초록]
{abstract}"""

    def get_skill_supplement(self, skill_name: str) -> str:
        """
        스킬별 보조 가이드 반환 (prompts.yaml과 함께 사용)

        Args:
            skill_name: 스킬 이름

        Returns:
            보조 가이드 텍스트
        """
        if skill_name not in self.SKILL_SUPPLEMENTS:
            skill_name = "peer-review"
        return self.SKILL_SUPPLEMENTS[skill_name]

    def get_skill_prompt(
        self,
        skill_name: str,
        paper_info: Dict[str, Any],
        language: str = "ko"
    ) -> str:
        """
        [Deprecated] 기존 호환성을 위해 유지
        새로운 방식: prompts.yaml + get_skill_supplement() 조합 사용
        """
        if skill_name not in self.SKILL_SUPPLEMENTS:
            skill_name = "peer-review"

        supplement = self.SKILL_SUPPLEMENTS[skill_name]
        paper_text = self._format_paper_info(paper_info)

        return f"""다음 논문에 대한 리뷰를 작성해주세요.

{paper_text}

{supplement}"""

    async def fetch_skill_docs_async(self, skill_name: str) -> Optional[str]:
        """
        MCP 서버에서 스킬 문서 비동기 로드 (캐시 지원)

        Args:
            skill_name: 스킬 이름

        Returns:
            스킬 문서 내용 (없으면 None)
        """
        if skill_name in self._skill_docs_cache:
            return self._skill_docs_cache[skill_name]

        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client

            async with streamablehttp_client(
                url=self.config.server_url,
                timeout=self.config.timeout,
                sse_read_timeout=self.config.sse_read_timeout
            ) as (read_stream, write_stream, get_session_id):

                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # list_skills로 사용 가능한 스킬 확인
                    tools_result = await session.list_tools()
                    tool_names = [tool.name for tool in tools_result.tools]

                    if "read_skill_document" not in tool_names:
                        logger.warning("read_skill_document 도구가 없습니다")
                        return None

                    # 스킬 문서 로드
                    result = await session.call_tool(
                        name="read_skill_document",
                        arguments={"skill_name": skill_name}
                    )

                    if result.content:
                        for content_block in result.content:
                            if hasattr(content_block, 'text'):
                                doc = content_block.text
                                self._skill_docs_cache[skill_name] = doc
                                logger.info(f"스킬 문서 캐시됨: {skill_name}")
                                return doc

                    return None

        except Exception as e:
            logger.error(f"스킬 문서 로드 실패: {e}")
            return None

    def fetch_skill_docs(self, skill_name: str) -> Optional[str]:
        """스킬 문서 동기 로드"""
        try:
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.fetch_skill_docs_async(skill_name)
                    )
                    return future.result(timeout=60)
            except RuntimeError:
                return asyncio.run(self.fetch_skill_docs_async(skill_name))
        except Exception as e:
            logger.error(f"스킬 문서 동기 로드 실패: {e}")
            return None

    def generate_scientific_review(
        self,
        paper_info: Dict[str, Any],
        review_style: str = "peer-review",
        language: str = "ko",
        claude_client: Optional[Any] = None
    ) -> Optional[str]:
        """
        전문적인 과학 논문 리뷰 생성

        Args:
            paper_info: 논문 정보
            review_style: 리뷰 스타일
            language: 출력 언어
            claude_client: Claude 클라이언트 (제공 시 직접 리뷰 생성)

        Returns:
            생성된 리뷰 또는 프롬프트 (claude_client 없으면 프롬프트만 반환)
        """
        if review_style not in self.REVIEW_SKILLS:
            logger.warning(f"알 수 없는 리뷰 스타일: {review_style}, 기본값 사용")
            review_style = "peer-review"

        logger.info(f"Scientific 리뷰 생성 시작 - 스타일: {review_style}")

        # 프롬프트 생성
        prompt = self.get_skill_prompt(review_style, paper_info, language)

        # Claude 클라이언트가 제공되면 직접 리뷰 생성
        if claude_client is not None:
            try:
                response = claude_client.client.messages.create(
                    model=claude_client.model,
                    max_tokens=8000,
                    system=f"당신은 {review_style} 스타일의 전문 과학 논문 리뷰어입니다. 깊이 있고 비판적인 분석을 제공합니다.",
                    messages=[{"role": "user", "content": prompt}]
                )

                if response.content:
                    review = response.content[0].text
                    logger.info(f"Scientific 리뷰 생성 완료 - 길이: {len(review)} chars")
                    return review
            except Exception as e:
                logger.error(f"Claude API 리뷰 생성 실패: {e}")
                return None

        # Claude 클라이언트 없으면 프롬프트만 반환
        logger.info("Claude 클라이언트 미제공, 프롬프트만 반환")
        return prompt


def create_scientific_client(
    server_url: Optional[str] = None,
    timeout: float = 120.0
) -> ScientificMCPClient:
    """Scientific MCP 클라이언트 생성"""
    config = ScientificSkillConfig(timeout=timeout)
    if server_url:
        config.server_url = server_url
    return ScientificMCPClient(config)
