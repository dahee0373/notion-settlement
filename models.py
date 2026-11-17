from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class Channel(Base):
    """판매 채널 정보 (스마트스토어, 쿠팡, 자사몰 등)"""
    __tablename__ = "channels"

    code = Column(String(50), primary_key=True)  # NAVER, COUPANG 등
    name = Column(String(100), nullable=False)
    login_id = Column(String(100), nullable=True)
    login_pw = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    targets = relationship("SettlementTarget", back_populates="channel")
    rpa_logs = relationship("RpaExecutionLog", back_populates="channel")


class Seller(Base):
    """판매자 / 입점사 / 셀러 정보"""
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_number = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    platform_fee_rate = Column(Numeric(5, 4), default=0.03)  # 자사 플랫폼 기본 수수료율 (예: 3%)
    bank_name = Column(String(50), nullable=True)
    account_number = Column(String(100), nullable=True)
    account_holder = Column(String(100), nullable=True)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, HOLD, INACTIVE
    created_at = Column(DateTime, default=datetime.utcnow)

    targets = relationship("SettlementTarget", back_populates="seller")
    ledgers = relationship("SettlementLedger", back_populates="seller")


class SettlementTarget(Base):
    """정산 원천 데이터 (각 채널에서 다운로드/수집된 주문별 원천 레코드)"""
    __tablename__ = "settlement_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    channel_code = Column(String(50), ForeignKey("channels.code"), nullable=False)
    channel_order_id = Column(String(100), nullable=False)  # 채널별 주문번호
    order_item_name = Column(String(200), nullable=True)     # 상품명
    confirmed_date = Column(Date, nullable=False)           # 구매확정일자
    settlement_month = Column(String(7), nullable=False)     # 정산 대상월 (YYYY-MM)

    sale_amount = Column(Numeric(12, 2), nullable=False)     # 결제/판매금액
    channel_fee = Column(Numeric(12, 2), default=0)         # 채널 수수료
    shipping_fee = Column(Numeric(12, 2), default=0)        # 배송비
    platform_fee = Column(Numeric(12, 2), default=0)        # 자사 플랫폼 수수료
    net_payout = Column(Numeric(12, 2), nullable=False)      # 실정산 예상액

    is_refund = Column(Boolean, default=False)              # 환불/취소 건 여부
    status = Column(String(20), default="CONFIRMED")         # CONFIRMED, SETTLED, HOLD, OFFSET
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("Seller", back_populates="targets")
    channel = relationship("Channel", back_populates="targets")


class SettlementLedger(Base):
    """월별 최종 정산 원장"""
    __tablename__ = "settlement_ledgers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"), nullable=False)
    settlement_month = Column(String(7), nullable=False)     # YYYY-MM
    
    total_sales = Column(Numeric(12, 2), default=0)         # 총 판매금액
    total_channel_fees = Column(Numeric(12, 2), default=0)  # 총 채널 수수료
    total_platform_fees = Column(Numeric(12, 2), default=0) # 총 플랫폼 수수료
    total_shipping_fees = Column(Numeric(12, 2), default=0) # 총 배송비
    refund_offset = Column(Numeric(12, 2), default=0)       # 전월 기정산 건의 취소/환불 상계액
    carryover_in = Column(Numeric(12, 2), default=0)        # 전월 마이너스 이월 유입액
    final_payout = Column(Numeric(12, 2), default=0)        # 최종 실지급액
    carryover_out = Column(Numeric(12, 2), default=0)       # 익월로 이월될 마이너스 잔여액

    status = Column(String(20), default="DRAFT")            # DRAFT, APPROVED, PAID
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    seller = relationship("Seller", back_populates="ledgers")
    payouts = relationship("SettlementPayout", back_populates="ledger")


class SettlementPayout(Base):
    """지급 내역"""
    __tablename__ = "settlement_payouts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ledger_id = Column(Integer, ForeignKey("settlement_ledgers.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    bank_name = Column(String(50), nullable=True)
    account_number = Column(String(100), nullable=True)
    status = Column(String(20), default="SUCCESS")  # SUCCESS, FAILED
    paid_at = Column(DateTime, default=datetime.utcnow)

    ledger = relationship("SettlementLedger", back_populates="payouts")


class RpaExecutionLog(Base):
    """RPA 수집 작업 이력"""
    __tablename__ = "rpa_execution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_code = Column(String(50), ForeignKey("channels.code"), nullable=False)
    target_month = Column(String(7), nullable=False)
    status = Column(String(20), nullable=False)             # SUCCESS, FAILED, RUNNING
    downloaded_file = Column(String(255), nullable=True)
    records_count = Column(Integer, default=0)
    message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)

    channel = relationship("Channel", back_populates="rpa_logs")
