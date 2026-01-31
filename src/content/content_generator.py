"""
논문 리뷰 콘텐츠 생성기 (Claude 활용)
"""
import logging
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# 논문 리뷰 템플릿들 (Claude 사용 불가 시 fallback)
REVIEW_TEMPLATES = [
    """# 논문 제목 분석

이번 논문은 AI 분야의 중요한 발전을 보여주는 연구입니다.

## 핵심 내용

주요 기여 사항은 다음과 같습니다:

1. **혁신적인 접근 방법**: 새로운 알고리즘을 통해 기존 방법보다 성능이 향상되었습니다.

2. **실험 결과**: 다양한 데이터셋에서 검증되어 신뢰성을 입증했습니다.

3. **실용적 가치**: 실제 산업 환경에 적용 가능한 실용적인 솔루션을 제시합니다.

## 개인적인 생각

이 논문은 향후 연구 방향에 큰 영향을 미칠 것으로 생각됩니다. 특히 [주요 기여] 부분이 인상적이었습니다.

## 결론

AI 분야의 지속적인 발전을 보여주는 의미 있는 연구라고 평가합니다.

---

*이 리뷰는 AI 논문을 분석하고 정리한 내용입니다.*""",

    """# 논문 주요 내용 정리

본 논문에서는 최신 AI 기술을 활용한 새로운 방법론을 제안합니다.

## 연구 배경

기존 연구의 한계점을 극복하기 위한 새로운 접근이 필요했습니다.

## 제안 방법

주요 방법론은 다음과 같습니다:

- **아키텍처 설계**: 효율적인 네트워크 구조 제안
- **학습 전략**: 개선된 학습 알고리즘 적용
- **최적화 기법**: 성능 향상을 위한 최적화 방법

## 실험 및 평가

제안한 방법은 기존 방법 대비 다음과 같은 성능 향상을 보였습니다:

- 정확도: X% 향상
- 처리 속도: Y% 개선
- 리소스 효율성: Z% 개선

## 의의 및 한계점

이 연구의 의의:
- 실용적 가치 제공
- 새로운 연구 방향 제시

한계점:
- 특정 도메인에서만 검증됨
- 추가 실험이 필요한 부분 존재

## 향후 연구 방향

더 다양한 데이터셋에서의 검증과 실제 적용 사례 연구가 필요할 것으로 보입니다.

---

*AI 논문 리뷰입니다.*""",

    """# 논문 요약 및 분석

## 개요

이 논문은 최신 AI 기술 트렌드를 반영한 연구입니다.

## 주요 내용

### 1. 문제 정의

현재 AI 분야에서 해결해야 할 중요한 문제를 명확히 정의했습니다.

### 2. 해결 방법

제안하는 방법론의 핵심:

1. **기술적 혁신**: 새로운 알고리즘 제안
2. **실험 설계**: 체계적인 실험을 통한 검증
3. **성능 분석**: 상세한 분석을 통한 인사이트 제공

### 3. 결과

연구 결과는 다음과 같습니다:

- State-of-the-art 성능 달성
- 효율성과 정확도의 균형
- 실제 응용 가능성 입증

## 평가

**장점**:
- 명확한 문제 정의
- 체계적인 실험 설계
- 실용적 가치

**개선점**:
- 더 많은 비교 실험 필요
- 다양한 도메인 적용 검증

## 결론

이 논문은 AI 분야의 발전에 기여하는 의미 있는 연구입니다.

---

*AI 논문 리뷰 포스트입니다.*"""
]


def generate_paper_review_content(
    paper: Dict,
    claude_client: Optional["ClaudeClient"] = None,
    review_number: Optional[int] = None,
    review_model: Optional[str] = None,
    use_scientific_skills: bool = False,
    scientific_style: str = "peer-review"
) -> str:
    """
    논문 리뷰 콘텐츠 생성

    Args:
        paper: 논문 정보 (title, authors, year, abstract 등)
        claude_client: Claude 클라이언트 (None이면 템플릿 사용)
        review_number: 리뷰 번호 (선택)
        review_model: 리뷰 작성용 모델 (None이면 클라이언트 기본 모델 사용)
        use_scientific_skills: Scientific Skills 스타일 사용 여부
        scientific_style: Scientific Skills 스타일 (peer-review, literature-review 등)

    Returns:
        생성된 리뷰 콘텐츠 (마크다운)
    """
    # Claude 클라이언트가 있으면 사용
    if claude_client:
        try:
            review = claude_client.generate_paper_review(
                paper,
                language="ko",
                model=review_model,
                use_scientific_skills=use_scientific_skills,
                scientific_style=scientific_style
            )
            return review
        except Exception as e:
            # rate limit 등 예상 가능한 에러는 경고 레벨, 기타 에러는 에러 레벨
            error_msg = str(e)
            if "rate" in error_msg.lower() or "429" in error_msg or "overloaded" in error_msg.lower():
                logger.warning(f"Claude API 할당량 초과, 템플릿 사용: {type(e).__name__}")
            else:
                logger.error(f"Claude 리뷰 생성 실패, 템플릿 사용: {type(e).__name__}: {error_msg[:100]}")
    
    # 템플릿 사용 (fallback)
    import random
    template = random.choice(REVIEW_TEMPLATES)
    
    # 논문 정보로 템플릿 개인화
    if paper:
        template = template.replace('[주요 기여]', paper.get('title', '이 논문'))
        template = f"# {paper.get('title', '논문 리뷰')}\n\n**저자**: {', '.join(paper.get('authors', []))}\n**발행년도**: {paper.get('year', 'N/A')}\n**인용수**: {paper.get('citations', 'N/A')}\n\n---\n\n{template}"
    
    return template

