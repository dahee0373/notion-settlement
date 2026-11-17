import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List, Dict, Any, Tuple

class SmartExcelSettlementProcessor:
    """
    Notion Design Language System 기반
    엑셀 파일의 실제 수수료를 스스로 역산/분석하고 정제된 Notion 스타일의 정산 리포트를 출력하는 코어 엔진
    """

    COL_SYNONYMS = {
        "order_id": ["주문번호", "상품주문번호", "주문ID", "order_id", "order_no", "주문 번호"],
        "product_name": ["상품명", "업체상품명", "주문상품명", "품목명", "product_name"],
        "date": ["구매확정일", "정산기준일", "주문일", "결제일", "결제일시", "정산일", "date"],
        "sale_amount": ["결제금액", "판매금액", "결제액", "매출액", "주문금액", "총결제금액", "amount"],
        "fee": ["수수료", "채널수수료", "판매수수료", "네이버페이수수료", "수수료합계", "공제금액", "service_fee"],
        "link_fee": ["매출연동수수료"],
        "shipping_fee": ["배송비", "정산배송비", "배송비금액", "shipping_fee"],
        "net_amount": ["정산예정금액", "정산금액", "실정산액", "지급예정액", "실지급액", "net_amount"]
    }

    @classmethod
    def detect_column_index(cls, header: List[str], target_key: str) -> int:
        synonyms = cls.COL_SYNONYMS.get(target_key, [])
        for idx, col_name in enumerate(header):
            col_clean = str(col_name).strip().replace(" ", "")
            for syn in synonyms:
                if syn.replace(" ", "") in col_clean:
                    return idx
        return -1

    @classmethod
    def parse_excel_file(cls, file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active

        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return "기타 채널", []

        header_row_idx = 0
        max_cols = 0
        for i in range(min(10, len(rows))):
            valid_cells = [str(c).strip() for c in rows[i] if c is not None and str(c).strip() != ""]
            if len(valid_cells) > max_cols:
                max_cols = len(valid_cells)
                header_row_idx = i

        header = [str(c).strip() if c is not None else "" for c in rows[header_row_idx]]
        header_str = " ".join(header)

        if "네이버페이수수료" in header_str or "스마트스토어" in file_path.name or "네이버" in file_path.name:
            channel_name = "네이버 스마트스토어"
        elif "판매수수료" in header_str or "쿠팡" in file_path.name or "업체상품명" in header_str:
            channel_name = "쿠팡 윙"
        elif "카카오" in file_path.name:
            channel_name = "카카오 선물하기"
        elif "11번가" in file_path.name or "지마켓" in file_path.name:
            channel_name = "11번가/지마켓"
        elif "토스" in file_path.name or "KCP" in file_path.name or "자사몰" in file_path.name:
            channel_name = "자사몰/PG"
        else:
            channel_name = "일반 채널"

        idx_order_id = cls.detect_column_index(header, "order_id")
        idx_product = cls.detect_column_index(header, "product_name")
        idx_date = cls.detect_column_index(header, "date")
        idx_sale = cls.detect_column_index(header, "sale_amount")
        idx_fee = cls.detect_column_index(header, "fee")
        idx_link_fee = cls.detect_column_index(header, "link_fee")
        idx_shipping = cls.detect_column_index(header, "shipping_fee")
        idx_net = cls.detect_column_index(header, "net_amount")

        records = []
        for row in rows[header_row_idx + 1:]:
            if not row or not any(row):
                continue

            order_id = str(row[idx_order_id]) if idx_order_id != -1 and row[idx_order_id] is not None else f"ORD-{len(records)+1}"
            product_name = str(row[idx_product]) if idx_product != -1 and row[idx_product] is not None else "상품"

            date_val = date.today()
            if idx_date != -1 and row[idx_date] is not None:
                raw_d = row[idx_date]
                if isinstance(raw_d, (datetime, date)):
                    date_val = raw_d if isinstance(raw_d, date) else raw_d.date()
                else:
                    try:
                        date_val = datetime.strptime(str(raw_d).strip()[:10], "%Y-%m-%d").date()
                    except Exception:
                        pass

            def to_decimal(val) -> Decimal:
                if val is None:
                    return Decimal("0")
                s = str(val).strip().replace(",", "").replace("원", "")
                try:
                    return Decimal(s)
                except Exception:
                    return Decimal("0")

            sale_amount = to_decimal(row[idx_sale]) if idx_sale != -1 else Decimal("0")
            shipping_fee = to_decimal(row[idx_shipping]) if idx_shipping != -1 else Decimal("0")
            net_amount = to_decimal(row[idx_net]) if idx_net != -1 else Decimal("0")

            if idx_fee != -1 and row[idx_fee] is not None:
                fee = to_decimal(row[idx_fee])
                if idx_link_fee != -1:
                    fee += to_decimal(row[idx_link_fee])
            elif idx_net != -1 and net_amount != Decimal("0") and sale_amount != Decimal("0"):
                fee = sale_amount + shipping_fee - net_amount
            else:
                fee = Decimal("0")

            is_refund = sale_amount < 0

            if sale_amount > 0 and fee >= 0:
                calc_rate = (fee / sale_amount * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                calc_rate = Decimal("0.0")

            records.append({
                "channel": channel_name,
                "order_id": order_id,
                "product_name": product_name,
                "date": date_val.strftime("%Y-%m-%d"),
                "sale_amount": sale_amount,
                "fee": fee,
                "calc_rate": float(calc_rate),
                "shipping_fee": shipping_fee,
                "is_refund": is_refund
            })

        return channel_name, records

    @classmethod
    def calculate_settlement(cls, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_sales = Decimal("0")
        total_fee = Decimal("0")
        total_shipping_fee = Decimal("0")
        refund_offset = Decimal("0")

        channel_breakdown = {}

        for rec in records:
            ch = rec["channel"]
            if ch not in channel_breakdown:
                channel_breakdown[ch] = {
                    "count": 0,
                    "sales": Decimal("0"),
                    "fee": Decimal("0"),
                    "shipping_fee": Decimal("0"),
                    "refund_amount": Decimal("0"),
                    "effective_rate_percent": 0.0
                }

            channel_breakdown[ch]["count"] += 1

            if rec["is_refund"] or rec["sale_amount"] < 0:
                net_loss = abs(rec["sale_amount"] - rec["fee"] + rec["shipping_fee"])
                refund_offset += net_loss
                channel_breakdown[ch]["refund_amount"] += net_loss
            else:
                sale = rec["sale_amount"]
                fee = rec["fee"]
                ship = rec["shipping_fee"]

                total_sales += sale
                total_fee += fee
                total_shipping_fee += ship

                channel_breakdown[ch]["sales"] += sale
                channel_breakdown[ch]["fee"] += fee
                channel_breakdown[ch]["shipping_fee"] += ship

        for ch, d in channel_breakdown.items():
            if d["sales"] > 0:
                eff_rate = (d["fee"] / d["sales"] * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                d["effective_rate_percent"] = float(eff_rate)
            else:
                d["effective_rate_percent"] = 0.0

        if total_sales > 0:
            overall_rate = float((total_fee / total_sales * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        else:
            overall_rate = 0.0

        net_amount = total_sales - total_fee + total_shipping_fee - refund_offset
        carryover_out = Decimal("0")
        if net_amount >= 0:
            final_payout = net_amount
        else:
            final_payout = Decimal("0")
            carryover_out = abs(net_amount)

        return {
            "total_count": len(records),
            "total_sales": total_sales,
            "total_fee": total_fee,
            "overall_rate_percent": overall_rate,
            "total_shipping_fee": total_shipping_fee,
            "refund_offset": refund_offset,
            "final_payout": final_payout,
            "carryover_out": carryover_out,
            "channel_breakdown": channel_breakdown,
            "records": records
        }

    @classmethod
    def export_settlement_excel(cls, summary: Dict[str, Any], output_path: Path):
        """Notion 디자인 토큰을 100% 반영한 프리미엄 엑셀 리포트 출력"""
        wb = openpyxl.Workbook()
        ws_summary = wb.active
        ws_summary.title = "Notion Summary"
        ws_summary.views.sheetView[0].showGridLines = True

        # Notion Typography & Color Palette
        font_name = "Segoe UI"
        title_font = Font(name=font_name, size=15, bold=True, color="000000")  # Ink
        meta_font = Font(name=font_name, size=9, color="615D59")               # Ink-muted
        th_font = Font(name=font_name, size=9, bold=True, color="31302E")      # Ink-secondary
        td_font = Font(name=font_name, size=9, color="31302E")
        bold_td_font = Font(name=font_name, size=9, bold=True, color="000000")
        payout_font = Font(name=font_name, size=11, bold=True, color="0075DE") # Notion Blue

        # Fills (Warm Paper Soft & Clean Card Surface)
        canvas_soft_fill = PatternFill(start_color="F6F5F4", end_color="F6F5F4", fill_type="solid")
        surface_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        highlight_fill = PatternFill(start_color="EEF6FD", end_color="EEF6FD", fill_type="solid") # Notion Soft Blue

        # Hairline Border (#E6E6E6)
        hairline = Border(
            left=Side(style='thin', color='E6E6E6'),
            right=Side(style='thin', color='E6E6E6'),
            top=Side(style='thin', color='E6E6E6'),
            bottom=Side(style='thin', color='E6E6E6')
        )
        double_hairline = Border(
            left=Side(style='thin', color='E6E6E6'),
            right=Side(style='thin', color='E6E6E6'),
            top=Side(style='thin', color='E6E6E6'),
            bottom=Side(style='double', color='0075DE')
        )

        # Title Block
        ws_summary["B2"] = "Notion Settlement Workspace"
        ws_summary["B2"].font = title_font
        ws_summary["B3"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Transactions: {summary['total_count']} items  |  Effective Rate: {summary['overall_rate_percent']:.2f}%"
        ws_summary["B3"].font = meta_font

        # Summary Table
        headers = ["구분 (Category)", "정산 금액 (Amount)", "설명 (Description)"]
        for col_idx, h in enumerate(headers, start=2):
            cell = ws_summary.cell(row=5, column=col_idx, value=h)
            cell.font = th_font
            cell.fill = canvas_soft_fill
            cell.border = hairline
            cell.alignment = Alignment(horizontal="center", vertical="center")

        items = [
            ("(+) 총 판매금액", summary["total_sales"], "정상 결제 주문 총 판매액"),
            (f"(-) 총 채널 수수료 ({summary['overall_rate_percent']:.2f}%)", summary["total_fee"], "엑셀 원본에서 역산된 실제 공제 수수료"),
            ("(+) 배송비 정산액", summary["total_shipping_fee"], "고객 결제 배송비"),
            ("(-) 반품/환불 상계액", summary["refund_offset"], "반품/환불 주문 자동 차감액"),
            ("(=) 최종 실지급액", summary["final_payout"], "판매자 통장 실입금 확정액"),
            ("(→) 익월 마이너스 이월액", summary["carryover_out"], "정산금이 음수일 경우 다음 달 이월")
        ]

        for idx, (label, val, note) in enumerate(items, start=6):
            cell_lbl = ws_summary.cell(row=idx, column=2, value=label)
            cell_val = ws_summary.cell(row=idx, column=3, value=int(val))
            cell_note = ws_summary.cell(row=idx, column=4, value=note)

            is_payout = (idx == 10)
            cell_lbl.font = payout_font if is_payout else (bold_td_font if idx == 6 else td_font)
            cell_val.font = payout_font if is_payout else (bold_td_font if idx == 6 else td_font)
            cell_note.font = meta_font

            cell_val.number_format = "#,##0"
            cell_val.alignment = Alignment(horizontal="right")
            cell_note.alignment = Alignment(horizontal="left")

            fill = highlight_fill if is_payout else surface_fill
            border = double_hairline if is_payout else hairline

            cell_lbl.fill = fill
            cell_val.fill = fill
            cell_note.fill = fill
            cell_lbl.border = border
            cell_val.border = border
            cell_note.border = border

        # Channel Breakdown Table
        start_ch_row = 14
        ws_summary.cell(row=start_ch_row, column=2, value="[Channel Breakdown]").font = bold_td_font

        ch_headers = ["채널명", "실효 수수료율", "건수", "총 매출액", "공제 수수료", "배송비", "환불 상계액"]
        for col_idx, h in enumerate(ch_headers, start=2):
            cell = ws_summary.cell(row=start_ch_row + 1, column=col_idx, value=h)
            cell.font = th_font
            cell.fill = canvas_soft_fill
            cell.border = hairline
            cell.alignment = Alignment(horizontal="center")

        curr_row = start_ch_row + 2
        for ch_name, data in summary["channel_breakdown"].items():
            ws_summary.cell(row=curr_row, column=2, value=ch_name).border = hairline
            ws_summary.cell(row=curr_row, column=3, value=f"{data['effective_rate_percent']:.2f}%").border = hairline
            ws_summary.cell(row=curr_row, column=4, value=data["count"]).border = hairline
            ws_summary.cell(row=curr_row, column=5, value=int(data["sales"])).border = hairline
            ws_summary.cell(row=curr_row, column=6, value=int(data["fee"])).border = hairline
            ws_summary.cell(row=curr_row, column=7, value=int(data["shipping_fee"])).border = hairline
            ws_summary.cell(row=curr_row, column=8, value=int(data["refund_amount"])).border = hairline

            ws_summary.cell(row=curr_row, column=3).alignment = Alignment(horizontal="center")
            ws_summary.cell(row=curr_row, column=4).alignment = Alignment(horizontal="center")
            for c in range(5, 9):
                ws_summary.cell(row=curr_row, column=c).number_format = "#,##0"
                ws_summary.cell(row=curr_row, column=c).alignment = Alignment(horizontal="right")
            curr_row += 1

        for col in ws_summary.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_summary.column_dimensions[col_letter].width = max(max_len + 4, 13)

        # Detail Statement Sheet
        ws_detail = wb.create_sheet(title="Audit Records")
        ws_detail.views.sheetView[0].showGridLines = True

        detail_headers = ["채널", "주문번호", "상품명", "기준일자", "판매금액", "수수료", "실효 요율", "배송비", "구분"]
        for col_idx, h in enumerate(detail_headers, start=1):
            cell = ws_detail.cell(row=1, column=col_idx, value=h)
            cell.font = th_font
            cell.fill = canvas_soft_fill
            cell.border = hairline
            cell.alignment = Alignment(horizontal="center")

        for r_idx, rec in enumerate(summary["records"], start=2):
            ws_detail.cell(row=r_idx, column=1, value=rec["channel"]).alignment = Alignment(horizontal="center")
            ws_detail.cell(row=r_idx, column=2, value=rec["order_id"]).alignment = Alignment(horizontal="center")
            ws_detail.cell(row=r_idx, column=3, value=rec["product_name"])
            ws_detail.cell(row=r_idx, column=4, value=rec["date"]).alignment = Alignment(horizontal="center")

            c_sale = ws_detail.cell(row=r_idx, column=5, value=int(rec["sale_amount"]))
            c_fee = ws_detail.cell(row=r_idx, column=6, value=int(rec["fee"]))
            c_rate = ws_detail.cell(row=r_idx, column=7, value=f"{rec['calc_rate']:.2f}%")
            c_ship = ws_detail.cell(row=r_idx, column=8, value=int(rec["shipping_fee"]))
            c_type = ws_detail.cell(row=r_idx, column=9, value="반품" if rec["is_refund"] else "정상")

            c_sale.number_format = "#,##0"
            c_fee.number_format = "#,##0"
            c_ship.number_format = "#,##0"
            c_sale.alignment = Alignment(horizontal="right")
            c_fee.alignment = Alignment(horizontal="right")
            c_rate.alignment = Alignment(horizontal="center")
            c_ship.alignment = Alignment(horizontal="right")
            c_type.alignment = Alignment(horizontal="center")

            for col_idx in range(1, 10):
                ws_detail.cell(row=r_idx, column=col_idx).border = hairline

            if rec["is_refund"]:
                c_type.font = Font(name=font_name, color="DD5B00", bold=True) # Notion Sticker Orange

        for col in ws_detail.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_detail.column_dimensions[col_letter].width = max(max_len + 4, 12)

        wb.save(output_path)
