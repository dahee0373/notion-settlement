from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from config import DOWNLOAD_DIR
from models import Channel, Seller, SettlementTarget, RpaExecutionLog
from rpa.base_scraper import SmartstoreRpaScraper, CoupangRpaScraper
from rpa.excel_parser import ExcelSettlementParser

class RpaCollectionService:
    """RPA 자동 다운로드 및 엑셀 파싱/적재 오케스트레이션 서비스"""

    @classmethod
    def get_scraper(cls, channel_code: str):
        if channel_code == "NAVER":
            return SmartstoreRpaScraper(DOWNLOAD_DIR)
        elif channel_code == "COUPANG":
            return CoupangRpaScraper(DOWNLOAD_DIR)
        else:
            raise ValueError(f"지원하지 않는 채널 코드입니다: {channel_code}")

    @classmethod
    def collect_channel_data(
        cls,
        db: Session,
        channel_code: str,
        target_month: str,
        seller_id: int
    ) -> Dict[str, Any]:
        """지정 채널에 접속하여 전월 정산자료를 자동 다운로드하고 DB에 적재합니다."""
        channel = db.query(Channel).filter(Channel.code == channel_code).first()
        seller = db.query(Seller).filter(Seller.id == seller_id).first()

        if not channel:
            raise ValueError(f"채널 정보를 찾을 수 없습니다: {channel_code}")
        if not seller:
            raise ValueError(f"판매자 정보를 찾을 수 없습니다: {seller_id}")

        scraper = cls.get_scraper(channel_code)
        
        try:
            # 1. RPA를 통한 정산 엑셀 파일 다운로드
            downloaded_file: Path = scraper.download_settlement_excel(
                target_month=target_month,
                login_id=channel.login_id,
                login_pw=channel.login_pw
            )

            # 2. 다운로드된 파일 파싱 및 표준화
            raw_records = ExcelSettlementParser.parse(
                file_path=downloaded_file,
                channel_code=channel_code,
                target_month=target_month
            )

            # 3. 데이터베이스 적재 (중복 방지 멱등성 보장)
            saved_count = 0
            skipped_count = 0

            for rec in raw_records:
                existing = db.query(SettlementTarget).filter(
                    SettlementTarget.channel_code == rec["channel_code"],
                    SettlementTarget.channel_order_id == rec["channel_order_id"],
                    SettlementTarget.settlement_month == target_month
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                # 자사 플랫폼 수수료 계산 (판매액 * 셀러 수수료율)
                sale_amt = rec["sale_amount"]
                platform_fee = (sale_amt * Decimal(str(seller.platform_fee_rate))).quantize(Decimal("1")) if sale_amt > 0 else Decimal(0)
                
                # 순정산액 = 결제액 - 채널수수료 + 배송비 - 플랫폼수수료
                net_payout = rec["sale_amount"] - rec["channel_fee"] + rec["shipping_fee"] - platform_fee

                target = SettlementTarget(
                    seller_id=seller.id,
                    channel_code=rec["channel_code"],
                    channel_order_id=rec["channel_order_id"],
                    order_item_name=rec["order_item_name"],
                    confirmed_date=rec["confirmed_date"],
                    settlement_month=target_month,
                    sale_amount=rec["sale_amount"],
                    channel_fee=rec["channel_fee"],
                    shipping_fee=rec["shipping_fee"],
                    platform_fee=platform_fee,
                    net_payout=net_payout,
                    is_refund=rec["is_refund"],
                    status="CONFIRMED"
                )
                db.add(target)
                saved_count += 1

            # 4. RPA 로그 기록
            log = RpaExecutionLog(
                channel_code=channel_code,
                target_month=target_month,
                status="SUCCESS",
                downloaded_file=str(downloaded_file.name),
                records_count=saved_count,
                message=f"성공적으로 {saved_count}건 적재 완료 (중복 제외 {skipped_count}건)"
            )
            db.add(log)
            db.commit()

            return {
                "channel_code": channel_code,
                "target_month": target_month,
                "saved_count": saved_count,
                "skipped_count": skipped_count,
                "downloaded_file": downloaded_file.name,
                "status": "SUCCESS"
            }

        except Exception as e:
            db.rollback()
            log = RpaExecutionLog(
                channel_code=channel_code,
                target_month=target_month,
                status="FAILED",
                records_count=0,
                message=str(e)
            )
            db.add(log)
            db.commit()
            raise e

    @classmethod
    def collect_all_active_channels(cls, db: Session, target_month: str, seller_id: int) -> List[Dict[str, Any]]:
        """활성화된 모든 채널에 대해 일괄 RPA 자동 수집을 실행합니다."""
        channels = db.query(Channel).filter(Channel.is_active == True).all()
        results = []
        for ch in channels:
            res = cls.collect_channel_data(db, ch.code, target_month, seller_id)
            results.append(res)
        return results
