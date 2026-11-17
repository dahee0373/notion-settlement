from decimal import Decimal
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from models import Seller, SettlementTarget, SettlementLedger, SettlementPayout

class MonthlySettlementService:
    """월 정산 집계, 환불 상계, 마이너스 이월 및 정산서 산출 서비스"""

    @classmethod
    def calculate_monthly_settlement(
        cls,
        db: Session,
        seller_id: int,
        target_month: str
    ) -> SettlementLedger:
        """
        특정 판매자의 특정 월(YYYY-MM) 정산을 집계하고 정산 원장(Ledger)을 생성/갱신합니다.
        """
        seller = db.query(Seller).filter(Seller.id == seller_id).first()
        if not seller:
            raise ValueError(f"판매자 ID {seller_id}를 찾을 수 없습니다.")

        # 1. 대상 월의 정산 원천 레코드 전체 조회
        targets: List[SettlementTarget] = db.query(SettlementTarget).filter(
            SettlementTarget.seller_id == seller_id,
            SettlementTarget.settlement_month == target_month
        ).all()

        if not targets:
            raise ValueError(f"{target_month} 월에 수집된 정산 대상 데이터가 없습니다.")

        # 2. 항목별 집계
        total_sales = Decimal("0")
        total_channel_fees = Decimal("0")
        total_platform_fees = Decimal("0")
        total_shipping_fees = Decimal("0")
        refund_offset = Decimal("0")  # 취소/환불로 인한 상계 차감액

        for t in targets:
            if t.is_refund or t.sale_amount < 0:
                # 환불/반품 건: 고객 환불액(음수) -> 상계 차감액으로 합산
                refund_offset += abs(Decimal(str(t.net_payout)))
            else:
                total_sales += Decimal(str(t.sale_amount))
                total_channel_fees += Decimal(str(t.channel_fee))
                total_platform_fees += Decimal(str(t.platform_fee))
                total_shipping_fees += Decimal(str(t.shipping_fee))

        # 3. 전월 마이너스 이월액(carryover_in) 확인
        # 이전 월 구하기 (예: 2026-10 -> 2026-09)
        year, month = map(int, target_month.split("-"))
        if month == 1:
            prev_month = f"{year - 1}-12"
        else:
            prev_month = f"{year}-{month - 1:02d}"

        prev_ledger = db.query(SettlementLedger).filter(
            SettlementLedger.seller_id == seller_id,
            SettlementLedger.settlement_month == prev_month
        ).first()

        carryover_in = Decimal(str(prev_ledger.carryover_out)) if prev_ledger and prev_ledger.carryover_out else Decimal("0")

        # 4. 정산금 계산
        # 순매출 = 총판매금액 - 채널수수료 - 자사플랫폼수수료 + 배송비
        net_sales = total_sales - total_channel_fees - total_platform_fees + total_shipping_fees

        # 잠정 지급액 = 순매출 - 환불상계액 - 전월이월액
        provisional_payout = net_sales - refund_offset - carryover_in

        if provisional_payout >= 0:
            final_payout = provisional_payout
            carryover_out = Decimal("0")
        else:
            final_payout = Decimal("0")
            carryover_out = abs(provisional_payout)  # 당월 미차감분은 다음달로 이월

        # 5. 기존 원장 존재 여부 확인 후 갱신 또는 신규 생성 (멱등성 보장)
        ledger = db.query(SettlementLedger).filter(
            SettlementLedger.seller_id == seller_id,
            SettlementLedger.settlement_month == target_month
        ).first()

        if not ledger:
            ledger = SettlementLedger(
                seller_id=seller_id,
                settlement_month=target_month
            )
            db.add(ledger)

        ledger.total_sales = total_sales
        ledger.total_channel_fees = total_channel_fees
        ledger.total_platform_fees = total_platform_fees
        ledger.total_shipping_fees = total_shipping_fees
        ledger.refund_offset = refund_offset
        ledger.carryover_in = carryover_in
        ledger.final_payout = final_payout
        ledger.carryover_out = carryover_out
        ledger.status = "DRAFT"

        db.commit()
        db.refresh(ledger)
        return ledger

    @classmethod
    def approve_and_payout(cls, db: Session, ledger_id: int) -> SettlementPayout:
        """관리자가 정산 원장을 최종 검토 후 승인(APPROVE)하고 지급(PAY) 완료 처리합니다."""
        ledger = db.query(SettlementLedger).filter(SettlementLedger.id == ledger_id).first()
        if not ledger:
            raise ValueError(f"정산 원장 ID {ledger_id}를 찾을 수 없습니다.")

        if ledger.status == "PAID":
            raise ValueError("이미 지급 완료된 정산 원장입니다.")

        seller = ledger.seller
        ledger.status = "PAID"
        ledger.closed_at = datetime.utcnow()

        payout = SettlementPayout(
            ledger_id=ledger.id,
            amount=ledger.final_payout,
            bank_name=seller.bank_name,
            account_number=seller.account_number,
            status="SUCCESS",
            paid_at=datetime.utcnow()
        )
        db.add(payout)
        db.commit()
        db.refresh(payout)
        return payout

    @classmethod
    def get_settlement_statement(cls, db: Session, seller_id: int, target_month: str) -> Dict[str, Any]:
        """월간 정산 명세서 리포트 데이터 조회"""
        ledger = db.query(SettlementLedger).filter(
            SettlementLedger.seller_id == seller_id,
            SettlementLedger.settlement_month == target_month
        ).first()

        if not ledger:
            raise ValueError(f"{target_month} 월의 정산 원장이 존재하지 않습니다.")

        targets = db.query(SettlementTarget).filter(
            SettlementTarget.seller_id == seller_id,
            SettlementTarget.settlement_month == target_month
        ).all()

        channel_breakdown = {}
        for t in targets:
            code = t.channel_code
            if code not in channel_breakdown:
                channel_breakdown[code] = {
                    "count": 0,
                    "sales": Decimal(0),
                    "channel_fees": Decimal(0),
                    "shipping_fees": Decimal(0),
                    "platform_fees": Decimal(0)
                }
            channel_breakdown[code]["count"] += 1
            channel_breakdown[code]["sales"] += Decimal(str(t.sale_amount))
            channel_breakdown[code]["channel_fees"] += Decimal(str(t.channel_fee))
            channel_breakdown[code]["shipping_fees"] += Decimal(str(t.shipping_fee))
            channel_breakdown[code]["platform_fees"] += Decimal(str(t.platform_fee))

        return {
            "seller_name": ledger.seller.name,
            "business_number": ledger.seller.business_number,
            "settlement_month": ledger.settlement_month,
            "status": ledger.status,
            "summary": {
                "total_sales": float(ledger.total_sales),
                "total_channel_fees": float(ledger.total_channel_fees),
                "total_platform_fees": float(ledger.total_platform_fees),
                "total_shipping_fees": float(ledger.total_shipping_fees),
                "refund_offset": float(ledger.refund_offset),
                "carryover_in": float(ledger.carryover_in),
                "final_payout": float(ledger.final_payout),
                "carryover_out": float(ledger.carryover_out)
            },
            "channel_breakdown": {
                k: {
                    "count": v["count"],
                    "sales": float(v["sales"]),
                    "channel_fees": float(v["channel_fees"]),
                    "shipping_fees": float(v["shipping_fees"]),
                    "platform_fees": float(v["platform_fees"])
                }
                for k, v in channel_breakdown.items()
            }
        }
