"""
온라인 매출 정산 시스템 - 전체 파이프라인 데모 실행 스크립트
(RPA 자동 다운로드 -> 엑셀 파싱 -> 월 정산 집계 -> 환불 상계 -> 정산서 발행 -> 지급)
"""
import sys
from decimal import Decimal
from database import engine, Base, SessionLocal
from models import Channel, Seller
from services.rpa_service import RpaCollectionService
from services.settlement_service import MonthlySettlementService

def format_krw(val):
    return f"{int(val):,}원"

def run_demo():
    print("=" * 70)
    print(" [1] 온라인 매출 정산 시스템 초기화 및 데이터베이스 준비")
    print("=" * 70)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 데모 채널 및 판매자 생성
    naver = db.query(Channel).filter(Channel.code == "NAVER").first()
    if not naver:
        naver = Channel(code="NAVER", name="네이버 스마트스토어 센터", login_id="smartstore_admin", is_active=True)
        db.add(naver)

    coupang = db.query(Channel).filter(Channel.code == "COUPANG").first()
    if not coupang:
        coupang = Channel(code="COUPANG", name="쿠팡 윙(Wing)", login_id="coupang_wing_admin", is_active=True)
        db.add(coupang)

    seller = db.query(Seller).filter(Seller.id == 1).first()
    if not seller:
        seller = Seller(
            id=1,
            business_number="123-45-67890",
            name="(주)알파커머스",
            platform_fee_rate=Decimal("0.03"),
            bank_name="신한은행",
            account_number="110-123-456789",
            account_holder="(주)알파커머스"
        )
        db.add(seller)
    db.commit()
    print("-> 네이버/쿠팡 채널 및 데모 판매자((주)알파커머스) 준비 완료.")

    target_month = "2026-10"
    print("\n" + "=" * 70)
    print(f" [2] RPA 자동 수집 가동: {target_month}월 정산 엑셀 자동 다운로드 및 적재")
    print("=" * 70)
    
    results = RpaCollectionService.collect_all_active_channels(
        db=db,
        target_month=target_month,
        seller_id=1
    )
    for r in results:
        print(f" - [{r['channel_code']}] 다운로드 파일: {r['downloaded_file']} -> {r['saved_count']}건 신규 적재 (중복 {r['skipped_count']}건)")

    print("\n" + "=" * 70)
    print(f" [3] 월 정산 코어 엔진 실행: {target_month}월 집계 & 환불 상계(Offset)")
    print("=" * 70)
    ledger = MonthlySettlementService.calculate_monthly_settlement(
        db=db,
        seller_id=1,
        target_month=target_month
    )

    statement = MonthlySettlementService.get_settlement_statement(db, seller_id=1, target_month=target_month)
    summary = statement["summary"]

    print(f" * 정산 대상자     : {statement['seller_name']} ({statement['business_number']})")
    print(f" * 정산 대상월     : {statement['settlement_month']}")
    print(f" * 정산 원장 상태  : {statement['status']}")
    print("-" * 70)
    print(f" (+) 총 판매금액        : {format_krw(summary['total_sales'])}")
    print(f" (-) 총 채널 수수료     : {format_krw(summary['total_channel_fees'])}")
    print(f" (-) 자사 플랫폼 수수료 : {format_krw(summary['total_platform_fees'])}")
    print(f" (+) 배송비 정산액      : {format_krw(summary['total_shipping_fees'])}")
    print(f" (-) 전월 환불 상계액   : {format_krw(summary['refund_offset'])} (반품 건 차감)")
    print(f" (-) 전월 이월 차감액   : {format_krw(summary['carryover_in'])}")
    print("=" * 70)
    print(f" (★) 최종 실지급액      : {format_krw(summary['final_payout'])}")
    print(f" (→) 익월 마이너스 이월 : {format_krw(summary['carryover_out'])}")
    print("=" * 70)

    print("\n[채널별 세부 내역]")
    for ch, data in statement["channel_breakdown"].items():
        print(f" * [{ch:8s}] 거래건수: {data['count']}건 | 매출: {format_krw(data['sales']):>10s} | 수수료: {format_krw(data['channel_fees']):>8s} | 배송비: {format_krw(data['shipping_fees']):>8s}")

    print("\n" + "=" * 70)
    print(" [4] 관리자 최종 검토 및 정산금 지급(Payout) 승인")
    print("=" * 70)
    payout = MonthlySettlementService.approve_and_payout(db=db, ledger_id=ledger.id)
    print(f" -> 지급 완료 상태   : {payout.status}")
    print(f" -> 지급 은행 및 계좌: {payout.bank_name} {payout.account_number}")
    print(f" -> 이체 처리 금액   : {format_krw(payout.amount)}")
    print(f" -> 처리 완료 일시   : {payout.paid_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print(" 전체 정산 파이프라인이 성공적으로 완료되었습니다!")

    db.close()

if __name__ == "__main__":
    run_demo()
