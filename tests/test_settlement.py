import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Channel, Seller, SettlementTarget, SettlementLedger
from services.rpa_service import RpaCollectionService
from services.settlement_service import MonthlySettlementService

# In-memory SQLite for testing
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    # 초기 채널 및 판매자 생성
    naver = Channel(code="NAVER", name="네이버 스마트스토어", is_active=True)
    coupang = Channel(code="COUPANG", name="쿠팡 윙", is_active=True)
    seller = Seller(
        id=1,
        business_number="123-45-67890",
        name="테스트상점",
        platform_fee_rate=Decimal("0.03")
    )
    session.add_all([naver, coupang, seller])
    session.commit()

    yield session
    session.close()


def test_rpa_collection_and_idempotency(db_session):
    """RPA 자동 다운로드 및 엑셀 파싱 적재, 중복 방지(멱등성) 테스트"""
    target_month = "2026-10"

    # 1. 1차 수집 실행
    results = RpaCollectionService.collect_all_active_channels(
        db=db_session,
        target_month=target_month,
        seller_id=1
    )
    assert len(results) == 2
    total_saved = sum(r["saved_count"] for r in results)
    assert total_saved > 0

    # 2. 동일 월에 대해 2차 수집 재실행 -> 중복 건은 모두 스킵되어야 함
    results_second = RpaCollectionService.collect_all_active_channels(
        db=db_session,
        target_month=target_month,
        seller_id=1
    )
    for r in results_second:
        assert r["saved_count"] == 0
        assert r["skipped_count"] > 0


def test_monthly_settlement_calculation_with_offset(db_session):
    """월 정산 집계 및 환불 상계(Offset) 계산 검증"""
    target_month = "2026-10"

    # RPA 데이터 자동 수집
    RpaCollectionService.collect_all_active_channels(
        db=db_session,
        target_month=target_month,
        seller_id=1
    )

    # 월 정산 집계 실행
    ledger = MonthlySettlementService.calculate_monthly_settlement(
        db=db_session,
        seller_id=1,
        target_month=target_month
    )

    assert ledger.settlement_month == "2026-10"
    assert ledger.total_sales > 0
    assert ledger.total_channel_fees > 0
    assert ledger.total_platform_fees > 0
    assert ledger.refund_offset > 0  # 네이버 샘플에 포함된 반품건 상계액
    assert ledger.final_payout > 0
    assert ledger.carryover_out == 0


def test_negative_carryover_handling(db_session):
    """환불/상계액이 매출보다 커서 음수가 발생했을 때 0원 지급 및 익월 이월 처리 검증"""
    target_month = "2026-11"

    # 거액의 반품/환불 건 1건만 발생한 경우 시뮬레이션
    refund_target = SettlementTarget(
        seller_id=1,
        channel_code="NAVER",
        channel_order_id="ORD-REFUND-9999",
        order_item_name="대형 가전 반품",
        confirmed_date=pytest.importorskip("datetime").date(2026, 11, 5),
        settlement_month=target_month,
        sale_amount=Decimal("-500000"),
        channel_fee=Decimal("-15000"),
        shipping_fee=Decimal("0"),
        platform_fee=Decimal("0"),
        net_payout=Decimal("-485000"),
        is_refund=True,
        status="CONFIRMED"
    )
    db_session.add(refund_target)
    db_session.commit()

    ledger = MonthlySettlementService.calculate_monthly_settlement(
        db=db_session,
        seller_id=1,
        target_month=target_month
    )

    # 마이너스 정산이므로 당월 실지급액은 0원이어야 함
    assert ledger.final_payout == Decimal("0")
    # 잔여 마이너스 금액은 익월 이월액(carryover_out)으로 잡혀야 함
    assert ledger.carryover_out == Decimal("485000")
