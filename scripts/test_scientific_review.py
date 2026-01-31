#!/usr/bin/env python3
"""
Scientific Skills MCP를 사용한 논문 리뷰 생성 테스트

사용법:
    python scripts/test_scientific_review.py

    # 특정 스타일 지정
    python scripts/test_scientific_review.py --style literature-review

    # 논문 제목 지정
    python scripts/test_scientific_review.py --title "Attention Is All You Need"
"""
import sys
import argparse
import logging
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.client.scientific_mcp_client import create_scientific_client, ScientificMCPClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_scientific_review(
    title: str = "Attention Is All You Need",
    style: str = "peer-review"
):
    """Scientific Skills MCP 리뷰 생성 테스트"""

    print(f"\n{'='*60}")
    print("Scientific Skills MCP 클라이언트 테스트")
    print(f"{'='*60}\n")

    # 테스트용 논문 정보
    paper_info = {
        "title": title,
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
        "year": 2017,
        "citations": 100000,
        "url": "https://arxiv.org/abs/1706.03762",
        "abstract": """
        The dominant sequence transduction models are based on complex recurrent or
        convolutional neural networks that include an encoder and a decoder. The best
        performing models also connect the encoder and decoder through an attention
        mechanism. We propose a new simple network architecture, the Transformer,
        based solely on attention mechanisms, dispensing with recurrence and convolutions
        entirely. Experiments on two machine translation tasks show these models to be
        superior in quality while being more parallelizable and requiring significantly
        less time to train.
        """
    }

    print(f"논문 정보:")
    print(f"  제목: {paper_info['title']}")
    print(f"  저자: {', '.join(paper_info['authors'][:3])}...")
    print(f"  년도: {paper_info['year']}")
    print(f"  리뷰 스타일: {style}")
    print()

    # MCP 클라이언트 생성 및 리뷰 생성
    try:
        client = create_scientific_client(timeout=180)

        print("사용 가능한 리뷰 스킬:")
        for skill, desc in client.list_available_skills().items():
            marker = "→" if skill == style else " "
            print(f"  {marker} {skill}: {desc}")
        print()

        print(f"리뷰 생성 중... (스타일: {style})")
        print("-" * 40)

        review = client.generate_scientific_review(
            paper_info=paper_info,
            review_style=style,
            language="ko"
        )

        if review:
            print("\n생성된 리뷰:\n")
            print(review)
            print(f"\n{'='*60}")
            print(f"리뷰 길이: {len(review)} 글자")
            print(f"{'='*60}")

            # 파일로 저장
            output_path = project_root / "output" / f"test_scientific_review_{style}.md"
            output_path.parent.mkdir(exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# {paper_info['title']}\n\n")
                f.write(f"**리뷰 스타일**: {style}\n\n")
                f.write("---\n\n")
                f.write(review)
            print(f"\n저장됨: {output_path}")

        else:
            print("리뷰 생성 실패!")
            print("MCP 서버 연결을 확인해주세요.")

    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)
        return False

    return True


def test_with_claude_client(style: str = "peer-review"):
    """ClaudeClient를 통한 Scientific Skills 리뷰 테스트"""
    import yaml

    print(f"\n{'='*60}")
    print("ClaudeClient + Scientific Skills 통합 테스트")
    print(f"{'='*60}\n")

    # 설정 로드
    config_path = project_root / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    api_key = config.get('claude', {}).get('api_key')
    if not api_key:
        print("config.yaml에서 Claude API 키를 찾을 수 없습니다.")
        return False

    from src.client.claude_client import ClaudeClient

    # 테스트 논문
    paper = {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        "year": 2019,
        "citations": 80000,
        "url": "https://arxiv.org/abs/1810.04805",
        "abstract": """
        We introduce a new language representation model called BERT, which stands for
        Bidirectional Encoder Representations from Transformers. Unlike recent language
        representation models, BERT is designed to pre-train deep bidirectional
        representations from unlabeled text by jointly conditioning on both left and
        right context in all layers.
        """
    }

    client = ClaudeClient(api_key=api_key)

    print(f"논문: {paper['title']}")
    print(f"스타일: {style}")
    print()

    try:
        # Scientific Skills 사용
        review = client.generate_paper_review(
            paper=paper,
            language="ko",
            use_scientific_skills=True,
            scientific_style=style
        )

        print("생성된 리뷰 (처음 500자):\n")
        print(review[:500] + "..." if len(review) > 500 else review)
        print(f"\n총 길이: {len(review)} 글자")

    except Exception as e:
        logger.error(f"통합 테스트 오류: {e}", exc_info=True)
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Scientific Skills MCP 테스트")
    parser.add_argument(
        "--style",
        choices=["peer-review", "literature-review", "scientific-critical-thinking", "scientific-writing"],
        default="peer-review",
        help="리뷰 스타일 선택"
    )
    parser.add_argument(
        "--title",
        default="Attention Is All You Need",
        help="테스트할 논문 제목"
    )
    parser.add_argument(
        "--test-claude",
        action="store_true",
        help="ClaudeClient 통합 테스트"
    )

    args = parser.parse_args()

    if args.test_claude:
        success = test_with_claude_client(args.style)
    else:
        success = test_scientific_review(args.title, args.style)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
