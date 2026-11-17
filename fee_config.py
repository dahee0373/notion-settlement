import json
from pathlib import Path
from decimal import Decimal
from typing import Dict

CONFIG_FILE = Path("channel_fee_rates.json")

DEFAULT_FEE_RATES = {
    "네이버 스마트스토어": 3.85,  # 네이버페이(1.98~3.63%) + 매출연동(2%) 평균
    "쿠팡 윙": 10.8,              # 쿠팡 카테고리별 수수료 기본치
    "카카오 선물하기": 12.0,       # 카카오 커머스
    "11번가/지마켓": 13.0,          # 오픈마켓 기본
    "자사몰/PG(토스/KCP)": 3.3,   # 일반 PG 결제 수수료
    "기타/일반": 5.0
}

def load_fee_rates() -> Dict[str, float]:
    """저장된 플랫폼별 수수료율을 불러옵니다. 없으면 기본값 반환"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_FEE_RATES.copy()

def save_fee_rates(rates: Dict[str, float]):
    """플랫폼별 수수료율 설정을 JSON 파일로 영구 저장합니다."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(rates, f, ensure_ascii=False, indent=2)
