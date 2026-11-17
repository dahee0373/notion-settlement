import openpyxl
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any
from pathlib import Path

class ExcelSettlementParser:
    """다운로드된 쇼핑몰 정산 엑셀 파일을 읽어 표준 정산 레코드로 정규화하는 파서"""

    @classmethod
    def parse(cls, file_path: Path, channel_code: str, target_month: str) -> List[Dict[str, Any]]:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []

        header = [str(col).strip() if col is not None else "" for col in rows[0]]
        records = []

        if channel_code == "NAVER" or "네이버페이수수료" in header:
            records = cls._parse_naver(rows[1:], header, target_month)
        elif channel_code == "COUPANG" or "판매수수료" in header:
            records = cls._parse_coupang(rows[1:], header, target_month)
        else:
            records = cls._parse_generic(rows[1:], header, target_month)

        return records

    @staticmethod
    def _parse_naver(rows, header: List[str], target_month: str) -> List[Dict[str, Any]]:
        col_map = {col: i for i, col in enumerate(header)}
        records = []

        for row in rows:
            if not row or not any(row):
                continue

            order_id = str(row[col_map.get("주문번호", 0)])
            product_name = str(row[col_map.get("상품명", 1)]) if "상품명" in col_map else "상품"
            confirmed_raw = row[col_map.get("구매확정일", 2)]
            
            # 날짜 변환
            if isinstance(confirmed_raw, (datetime, date)):
                confirmed_date = confirmed_raw if isinstance(confirmed_raw, date) else confirmed_raw.date()
            else:
                try:
                    confirmed_date = datetime.strptime(str(confirmed_raw).strip()[:10], "%Y-%m-%d").date()
                except Exception:
                    confirmed_date = date.today()

            sale_amount = Decimal(str(row[col_map.get("결제금액", 3)] or 0))
            npay_fee = Decimal(str(row[col_map.get("네이버페이수수료", 4)] or 0))
            link_fee = Decimal(str(row[col_map.get("매출연동수수료", 5)] or 0)) if "매출연동수수료" in col_map else Decimal(0)
            channel_fee = npay_fee + link_fee

            shipping_fee = Decimal(str(row[col_map.get("배송비", 6)] or 0)) if "배송비" in col_map else Decimal(0)
            net_payout = Decimal(str(row[col_map.get("정산예정금액", 7)] or (sale_amount - channel_fee + shipping_fee)))

            is_refund = sale_amount < 0

            records.append({
                "channel_code": "NAVER",
                "channel_order_id": order_id,
                "order_item_name": product_name,
                "confirmed_date": confirmed_date,
                "settlement_month": target_month,
                "sale_amount": sale_amount,
                "channel_fee": channel_fee,
                "shipping_fee": shipping_fee,
                "net_payout": net_payout,
                "is_refund": is_refund
            })
        return records

    @staticmethod
    def _parse_coupang(rows, header: List[str], target_month: str) -> List[Dict[str, Any]]:
        col_map = {col: i for i, col in enumerate(header)}
        records = []

        for row in rows:
            if not row or not any(row):
                continue

            order_id = str(row[col_map.get("주문번호", 0)])
            product_name = str(row[col_map.get("업체상품명", 1)]) if "업체상품명" in col_map else "상품"
            confirmed_raw = row[col_map.get("정산기준일", 2)]

            if isinstance(confirmed_raw, (datetime, date)):
                confirmed_date = confirmed_raw if isinstance(confirmed_raw, date) else confirmed_raw.date()
            else:
                try:
                    confirmed_date = datetime.strptime(str(confirmed_raw).strip()[:10], "%Y-%m-%d").date()
                except Exception:
                    confirmed_date = date.today()

            sale_amount = Decimal(str(row[col_map.get("결제액", 3)] or 0))
            channel_fee = Decimal(str(row[col_map.get("판매수수료", 4)] or 0))
            shipping_fee = Decimal(str(row[col_map.get("배송비", 5)] or 0)) if "배송비" in col_map else Decimal(0)
            net_payout = Decimal(str(row[col_map.get("정산금액", 6)] or (sale_amount - channel_fee + shipping_fee)))

            is_refund = sale_amount < 0

            records.append({
                "channel_code": "COUPANG",
                "channel_order_id": order_id,
                "order_item_name": product_name,
                "confirmed_date": confirmed_date,
                "settlement_month": target_month,
                "sale_amount": sale_amount,
                "channel_fee": channel_fee,
                "shipping_fee": shipping_fee,
                "net_payout": net_payout,
                "is_refund": is_refund
            })
        return records

    @staticmethod
    def _parse_generic(rows, header: List[str], target_month: str) -> List[Dict[str, Any]]:
        col_map = {col: i for i, col in enumerate(header)}
        records = []

        for row in rows:
            if not row or not any(row):
                continue
            order_id = str(row[0])
            product_name = str(row[1]) if len(row) > 1 else "상품"
            confirmed_date = date.today()
            sale_amount = Decimal(str(row[2] or 0)) if len(row) > 2 else Decimal(0)
            channel_fee = Decimal(str(row[3] or 0)) if len(row) > 3 else Decimal(0)
            shipping_fee = Decimal(str(row[4] or 0)) if len(row) > 4 else Decimal(0)
            net_payout = sale_amount - channel_fee + shipping_fee

            records.append({
                "channel_code": "GENERIC",
                "channel_order_id": order_id,
                "order_item_name": product_name,
                "confirmed_date": confirmed_date,
                "settlement_month": target_month,
                "sale_amount": sale_amount,
                "channel_fee": channel_fee,
                "shipping_fee": shipping_fee,
                "net_payout": net_payout,
                "is_refund": sale_amount < 0
            })
        return records
