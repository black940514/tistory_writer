"""
카테고리 조회 테스트 스크립트
"""
import yaml
import logging
from pathlib import Path
from tistory_api import TistoryAPI

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG 레벨로 변경
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """카테고리 조회 테스트"""
    try:
        # 설정 파일 로드
        config_path = Path("config.yaml")
        if not config_path.exists():
            print("❌ config.yaml 파일을 찾을 수 없습니다.")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        tistory_config = config['tistory']
        
        # TistoryAPI 초기화
        if 'cookies' in tistory_config and tistory_config['cookies']:
            api = TistoryAPI(
                blog_name=tistory_config['blog_name'],
                cookies=tistory_config['cookies']
            )
        else:
            api = TistoryAPI(
                user_id=tistory_config['user_id'],
                user_pw=tistory_config['user_pw'],
                blog_name=tistory_config['blog_name']
            )
        
        # 카테고리 목록 조회
        print("\n📋 카테고리 목록 조회 중...")
        categories = api.get_category_list()
        
        print(f"\n✅ {len(categories)}개의 카테고리를 찾았습니다:")
        for cat in categories:
            print(f"  - {cat['name']} (ID: {cat['id']})")
        
        # PaperReview 카테고리 찾기
        category_name = config.get('category', {}).get('name', 'PaperReview')
        cat_id = api.get_category_id_by_name(category_name)
        
        if cat_id:
            print(f"\n✅ '{category_name}' 카테고리 ID: {cat_id}")
        else:
            print(f"\n⚠️ '{category_name}' 카테고리를 찾을 수 없습니다.")
            print("사용 가능한 카테고리 목록을 확인해주세요.")
        
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        print(f"❌ 오류: {e}")


if __name__ == "__main__":
    main()

