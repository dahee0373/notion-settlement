from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from decimal import Decimal

from database import engine, Base, get_db
import models
from models import Channel, Seller, SettlementLedger, RpaExecutionLog
from services.rpa_service import RpaCollectionService
from services.settlement_service import MonthlySettlementService

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Online Sales Settlement API (RPA Auto-Ingestion)",
    description="쇼핑몰(네이버, 쿠팡 등) 정산 자료 RPA 자동 수집 및 월 정산 자동화 시스템",
    version="1.0.0"
)

# Request Models
class RpaCollectRequest(BaseModel):
    target_month: str  # YYYY-MM
    seller_id: int
    channel_code: Optional[str] = None  # None이면 전체 활성 채널

class CalculateSettlementRequest(BaseModel):
    seller_id: int
    target_month: str  # YYYY-MM

@app.get("/")
def read_root():
    return {
        "message": "온라인 매출 정산 시스템 API가 정상 실행 중입니다.",
        "docs_url": "/docs"
    }

@app.post("/api/setup/init-demo-data", summary="데모용 채널 및 셀러 기본 데이터 생성")
def init_demo_data(db: Session = Depends(get_db)):
    """테스트를 위해 기본 채널(네이버, 쿠팡)과 데모 판매자 데이터를 초기화합니다."""
    # 채널 생성
    naver = db.query(Channel).filter(Channel.code == "NAVER").first()
    if not naver:
        naver = Channel(
            code="NAVER",
            name="네이버 스마트스토어 센터",
            login_id="smartstore_demo_seller",
            login_pw="demo_password!123",
            is_active=True
        )
        db.add(naver)

    coupang = db.query(Channel).filter(Channel.code == "COUPANG").first()
    if not coupang:
        coupang = Channel(
            code="COUPANG",
            name="쿠팡 윙(Wing)",
            login_id="coupang_wing_demo",
            login_pw="demo_password!123",
            is_active=True
        )
        db.add(coupang)

    # 판매자 생성
    seller = db.query(Seller).filter(Seller.id == 1).first()
    if not seller:
        seller = Seller(
            id=1,
            business_number="123-45-67890",
            name="(주)알파커머스",
            platform_fee_rate=Decimal("0.03"), # 자사 수수료 3%
            bank_name="신한은행",
            account_number="110-123-456789",
            account_holder="(주)알파커머스",
            status="ACTIVE"
        )
        db.add(seller)

    db.commit()
    return {"message": "데모 채널 및 판매자 데이터 초기화가 완료되었습니다.", "seller_id": 1}

@app.post("/api/rpa/collect", summary="RPA 자동 정산자료 다운로드 & 적재 실행")
def trigger_rpa_collection(req: RpaCollectRequest, db: Session = Depends(get_db)):
    """
    지정된 월의 쇼핑몰 어드민에 접속하여 정산 엑셀을 자동 다운로드하고 DB에 정규화 적재합니다.
    channel_code가 없으면 등록된 모든 활성 채널을 자동 수집합니다.
    """
    try:
        if req.channel_code:
            result = RpaCollectionService.collect_channel_data(
                db=db,
                channel_code=req.channel_code,
                target_month=req.target_month,
                seller_id=req.seller_id
            )
            return {"results": [result]}
        else:
            results = RpaCollectionService.collect_all_active_channels(
                db=db,
                target_month=req.target_month,
                seller_id=req.seller_id
            )
            return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/settlements/calculate", summary="월 정산 원장 집계 및 산출")
def calculate_monthly_settlement(req: CalculateSettlementRequest, db: Session = Depends(get_db)):
    """
    수집된 원천 데이터를 기반으로 전월 기정산 환불 상계, 마이너스 이월액을 반영하여 최종 정산 원장을 산출합니다.
    """
    try:
        ledger = MonthlySettlementService.calculate_monthly_settlement(
            db=db,
            seller_id=req.seller_id,
            target_month=req.target_month
        )
        return {
            "ledger_id": ledger.id,
            "seller_id": ledger.seller_id,
            "settlement_month": ledger.settlement_month,
            "total_sales": float(ledger.total_sales),
            "total_channel_fees": float(ledger.total_channel_fees),
            "total_platform_fees": float(ledger.total_platform_fees),
            "total_shipping_fees": float(ledger.total_shipping_fees),
            "refund_offset": float(ledger.refund_offset),
            "carryover_in": float(ledger.carryover_in),
            "final_payout": float(ledger.final_payout),
            "carryover_out": float(ledger.carryover_out),
            "status": ledger.status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/settlements/{ledger_id}/approve", summary="정산 승인 및 지급 완료")
def approve_and_payout(ledger_id: int, db: Session = Depends(get_db)):
    """관리자가 정산 원장을 확인 후 최종 승인 및 펌뱅킹 지급 처리를 실행합니다."""
    try:
        payout = MonthlySettlementService.approve_and_payout(db=db, ledger_id=ledger_id)
        return {
            "message": "정산 승인 및 지급 처리가 완료되었습니다.",
            "payout_id": payout.id,
            "amount": float(payout.amount),
            "status": payout.status,
            "paid_at": payout.paid_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/settlements/statement", summary="월간 정산 명세서 조회")
def get_statement(
    seller_id: int = Query(..., description="판매자 ID"),
    target_month: str = Query(..., description="정산월 (YYYY-MM)"),
    db: Session = Depends(get_db)
):
    """지정 판매자의 월별 정산 명세서 리포트(채널별 breakdown 포함)를 조회합니다."""
    try:
        statement = MonthlySettlementService.get_settlement_statement(
            db=db,
            seller_id=seller_id,
            target_month=target_month
        )
        return statement
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/rpa/logs", summary="RPA 실행 이력 조회")
def get_rpa_logs(db: Session = Depends(get_db)):
    logs = db.query(RpaExecutionLog).order_by(RpaExecutionLog.executed_at.desc()).limit(20).all()
    return [
        {
            "id": log.id,
            "channel_code": log.channel_code,
            "target_month": log.target_month,
            "status": log.status,
            "downloaded_file": log.downloaded_file,
            "records_count": log.records_count,
            "message": log.message,
            "executed_at": log.executed_at.isoformat()
        }
        for log in logs
    ]
