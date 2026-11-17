"""
온라인 매출 정산 자동화 프로그램 - Notion Design Language Edition
(Based on DESIGN-notion.md: Warm Paper Canvas, Notion Blue, Ink Hierarchy, Hairline Borders, Sticker Badges)
"""
import os
import sys
from pathlib import Path
from decimal import Decimal
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from excel_settlement_processor import SmartExcelSettlementProcessor

# Notion Design Tokens (from DESIGN-notion.md)
NOTION_COLORS = {
    "primary": "#0075de",          # Notion Blue (Action / Focus)
    "primary-active": "#005bab",   # Pressed state
    "secondary": "#213183",        # Deep Indigo (Hero "night" band)
    "canvas": "#ffffff",           # Surface / Pure White
    "canvas-soft": "#f6f5f4",      # Signature warm paper-soft canvas
    "surface": "#ffffff",          # Card surface
    "ink": "#000000",              # Primary text / Headings (~95% true black)
    "ink-secondary": "#31302e",    # Warm charcoal body
    "ink-muted": "#615d59",        # Stone gray supporting text
    "ink-faint": "#a39e98",        # Ash caption / metadata
    "hairline": "#e6e6e6",         # 1px card borders and dividers
    
    # Decorative Sticker Palette
    "accent-sky": "#62aef0",
    "accent-purple": "#d6b6f6",
    "accent-pink": "#ff64c8",
    "accent-orange": "#dd5b00",
    "accent-teal": "#2a9d99",
    "accent-green": "#1aae39",
    "accent-green-soft": "#e8f8ed",
    "accent-orange-soft": "#fdf1e8",
    "accent-sky-soft": "#eef6fd"
}

NOTION_FONTS = {
    "display": ("Segoe UI", 16, "bold"),
    "title": ("Segoe UI", 13, "bold"),
    "subtitle": ("Segoe UI", 9),
    "card-title": ("Segoe UI", 9, "bold"),
    "card-value": ("Segoe UI", 16, "bold"),
    "body": ("Segoe UI", 9),
    "button": ("Segoe UI", 10, "bold"),
    "mono": ("Consolas", 9),
    "eyebrow": ("Segoe UI", 8, "bold")
}

class NotionSettlementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Notion Settlement — 온라인 매출 정산")
        self.root.geometry("860x720")
        self.root.minsize(780, 620)
        self.root.configure(bg=NOTION_COLORS["canvas-soft"])

        self.selected_files = []
        self.current_summary = None

        self._init_theme()
        self._build_ui()

    def _init_theme(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # 기본 ttk 프레임 배경을 warm paper (canvas-soft)로 일치
        self.style.configure(".", background=NOTION_COLORS["canvas-soft"])
        self.style.configure("TFrame", background=NOTION_COLORS["canvas-soft"])
        self.style.configure("TLabel", background=NOTION_COLORS["canvas-soft"], foreground=NOTION_COLORS["ink-secondary"])
        self.style.configure("TLabelframe", background=NOTION_COLORS["canvas-soft"], bordercolor=NOTION_COLORS["hairline"])
        self.style.configure("TLabelframe.Label", background=NOTION_COLORS["canvas-soft"], foreground=NOTION_COLORS["ink"], font=NOTION_FONTS["title"])

    def _build_ui(self):
        # 1. Notion Hero Night Band (secondary: #213183)
        hero_frame = tk.Frame(self.root, bg=NOTION_COLORS["secondary"], height=88)
        hero_frame.pack(fill=tk.X)
        hero_frame.pack_propagate(False)

        hero_inner = tk.Frame(hero_frame, bg=NOTION_COLORS["secondary"])
        hero_inner.pack(fill=tk.BOTH, expand=True, padx=28, pady=16)

        # Eyebrow Pill
        pill_badge = tk.Label(
            hero_inner,
            text="● SETTLEMENT WORKSPACE",
            font=NOTION_FONTS["eyebrow"],
            bg="rgba(255, 255, 255, 0.15)" if sys.platform != "win32" else "#2c3e98",
            fg=NOTION_COLORS["accent-sky"],
            padx=8,
            pady=2
        )
        pill_badge.pack(anchor="w")

        title_lbl = tk.Label(
            hero_inner,
            text="온라인 매출 정산 워크스페이스",
            font=NOTION_FONTS["display"],
            fg="#ffffff",
            bg=NOTION_COLORS["secondary"]
        )
        title_lbl.pack(anchor="w", pady=(4, 0))

        sub_lbl = tk.Label(
            hero_inner,
            text="엑셀 파일의 수수료와 정산 데이터를 스스로 인식하여 1원 단위까지 정산 명세서를 산출합니다.",
            font=NOTION_FONTS["subtitle"],
            fg=NOTION_COLORS["ink-faint"],
            bg=NOTION_COLORS["secondary"]
        )
        sub_lbl.pack(anchor="w")

        # 메인 워크스페이스 컨테이너 (Warm Paper Canvas: #f6f5f4)
        main_container = tk.Frame(self.root, bg=NOTION_COLORS["canvas-soft"], padx=24, pady=16)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 2. File Ingestion Card (Feature Card with Hairline: #e6e6e6)
        file_card = tk.Frame(
            main_container,
            bg=NOTION_COLORS["surface"],
            highlightbackground=NOTION_COLORS["hairline"],
            highlightthickness=1,
            padx=18,
            pady=14
        )
        file_card.pack(fill=tk.X, pady=(0, 14))

        card_top = tk.Frame(file_card, bg=NOTION_COLORS["surface"])
        card_top.pack(fill=tk.X, pady=(0, 8))

        card_title = tk.Label(
            card_top,
            text="정산 엑셀 파일 (Input Documents)",
            font=NOTION_FONTS["title"],
            fg=NOTION_COLORS["ink"],
            bg=NOTION_COLORS["surface"]
        )
        card_title.pack(side=tk.LEFT)

        self.lbl_file_count = tk.Label(
            card_top,
            text="선택된 파일: 0개",
            font=NOTION_FONTS["subtitle"],
            fg=NOTION_COLORS["ink-muted"],
            bg=NOTION_COLORS["surface"]
        )
        self.lbl_file_count.pack(side=tk.RIGHT)

        # File Button Bar
        btn_bar = tk.Frame(file_card, bg=NOTION_COLORS["surface"])
        btn_bar.pack(fill=tk.X, pady=(0, 8))

        # Notion Utility Button
        self.btn_add_files = tk.Button(
            btn_bar,
            text="＋ 파일 가져오기 (.xlsx)",
            font=NOTION_FONTS["button"],
            bg=NOTION_COLORS["canvas-soft"],
            fg=NOTION_COLORS["ink"],
            activebackground=NOTION_COLORS["hairline"],
            activeforeground=NOTION_COLORS["ink"],
            relief=tk.FLAT,
            highlightbackground=NOTION_COLORS["hairline"],
            highlightthickness=1,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.choose_files
        )
        self.btn_add_files.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear_files = tk.Button(
            btn_bar,
            text="비우기",
            font=NOTION_FONTS["body"],
            bg=NOTION_COLORS["surface"],
            fg=NOTION_COLORS["ink-muted"],
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.clear_files
        )
        self.btn_clear_files.pack(side=tk.LEFT)

        # Listbox with clean hairline
        list_frame = tk.Frame(file_card, bg=NOTION_COLORS["surface"], highlightbackground=NOTION_COLORS["hairline"], highlightthickness=1)
        list_frame.pack(fill=tk.X)

        self.file_listbox = tk.Listbox(
            list_frame,
            height=3,
            font=NOTION_FONTS["body"],
            bg=NOTION_COLORS["canvas-soft"],
            fg=NOTION_COLORS["ink-secondary"],
            selectbackground=NOTION_COLORS["primary"],
            selectforeground="#ffffff",
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0
        )
        self.file_listbox.pack(fill=tk.X, padx=4, pady=4)

        # 3. Action Area: Primary CTA ("button-primary" — Notion Blue: #0075de)
        self.btn_run = tk.Button(
            main_container,
            text="정산 실행하기 (Run Settlement)",
            font=NOTION_FONTS["button"],
            bg=NOTION_COLORS["primary"],
            fg="#ffffff",
            activebackground=NOTION_COLORS["primary-active"],
            activeforeground="#ffffff",
            relief=tk.FLAT,
            pady=10,
            cursor="hand2",
            command=self.run_settlement
        )
        self.btn_run.pack(fill=tk.X, pady=(0, 14))

        # 4. Result Metrics Card (3 Notion Stat Tiles)
        metrics_container = tk.Frame(main_container, bg=NOTION_COLORS["canvas-soft"])
        metrics_container.pack(fill=tk.X, pady=(0, 14))

        self.card_sales = self._create_notion_metric_card(
            metrics_container,
            tag="GROSS SALES",
            title="총 판매금액",
            val="0원",
            tag_color=NOTION_COLORS["accent-sky"],
            val_color=NOTION_COLORS["ink"]
        )
        self.card_sales.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.card_fees = self._create_notion_metric_card(
            metrics_container,
            tag="DEDUCTIONS",
            title="총 채널 공제액",
            val="0원",
            tag_color=NOTION_COLORS["accent-orange"],
            val_color=NOTION_COLORS["ink-secondary"]
        )
        self.card_fees.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.card_payout = self._create_notion_metric_card(
            metrics_container,
            tag="NET PAYOUT",
            title="최종 실지급액",
            val="0원",
            tag_color=NOTION_COLORS["accent-green"],
            val_color=NOTION_COLORS["primary"]
        )
        self.card_payout.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 5. Detail Statement Card (Console/Report with Hairline Frame)
        detail_card = tk.Frame(
            main_container,
            bg=NOTION_COLORS["surface"],
            highlightbackground=NOTION_COLORS["hairline"],
            highlightthickness=1,
            padx=16,
            pady=12
        )
        detail_card.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

        detail_header = tk.Frame(detail_card, bg=NOTION_COLORS["surface"])
        detail_header.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            detail_header,
            text="정산 상세 명세 (Statement Audit)",
            font=NOTION_FONTS["title"],
            fg=NOTION_COLORS["ink"],
            bg=NOTION_COLORS["surface"]
        ).pack(side=tk.LEFT)

        self.lbl_rate_pill = tk.Label(
            detail_header,
            text="실효 수수료율: 대기중",
            font=NOTION_FONTS["eyebrow"],
            bg=NOTION_COLORS["canvas-soft"],
            fg=NOTION_COLORS["ink-muted"],
            padx=8,
            pady=2
        )
        self.lbl_rate_pill.pack(side=tk.RIGHT)

        self.txt_result = tk.Text(
            detail_card,
            font=NOTION_FONTS["mono"],
            bg=NOTION_COLORS["canvas-soft"],
            fg=NOTION_COLORS["ink-secondary"],
            relief=tk.FLAT,
            borderwidth=0,
            padx=10,
            pady=8,
            wrap=tk.WORD
        )
        self.txt_result.pack(fill=tk.BOTH, expand=True)
        self.txt_result.insert(tk.END, "문서를 추가하고 [정산 실행하기]를 누르면 엑셀 원본 데이터를 역산하여 명세를 표시합니다.\n")

        # 6. Export Button (Utility Button with Subtle Hairline)
        self.btn_export = tk.Button(
            main_container,
            text="↓ 엑셀 보고서 다운로드 (Export to .xlsx)",
            font=NOTION_FONTS["button"],
            bg=NOTION_COLORS["surface"],
            fg=NOTION_COLORS["ink"],
            activebackground=NOTION_COLORS["canvas-soft"],
            activeforeground=NOTION_COLORS["ink"],
            relief=tk.FLAT,
            highlightbackground=NOTION_COLORS["hairline"],
            highlightthickness=1,
            pady=9,
            cursor="hand2",
            state=tk.DISABLED,
            command=self.export_excel
        )
        self.btn_export.pack(fill=tk.X)

    def _create_notion_metric_card(self, parent, tag, title, val, tag_color, val_color):
        card = tk.Frame(
            parent,
            bg=NOTION_COLORS["surface"],
            highlightbackground=NOTION_COLORS["hairline"],
            highlightthickness=1,
            padx=16,
            pady=12
        )

        top_row = tk.Frame(card, bg=NOTION_COLORS["surface"])
        top_row.pack(fill=tk.X)

        tag_lbl = tk.Label(
            top_row,
            text=f"● {tag}",
            font=NOTION_FONTS["eyebrow"],
            fg=tag_color,
            bg=NOTION_COLORS["surface"]
        )
        tag_lbl.pack(side=tk.LEFT)

        title_lbl = tk.Label(
            card,
            text=title,
            font=NOTION_FONTS["card-title"],
            fg=NOTION_COLORS["ink-muted"],
            bg=NOTION_COLORS["surface"]
        )
        title_lbl.pack(anchor="w", pady=(4, 0))

        val_lbl = tk.Label(
            card,
            text=val,
            font=NOTION_FONTS["card-value"],
            fg=val_color,
            bg=NOTION_COLORS["surface"]
        )
        val_lbl.pack(anchor="w", pady=(2, 0))

        card.val_lbl = val_lbl
        return card

    def choose_files(self):
        filetypes = [("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        filenames = filedialog.askopenfilenames(title="정산할 엑셀 문서를 선택하세요", filetypes=filetypes)
        if filenames:
            for f in filenames:
                path = Path(f)
                if path not in self.selected_files:
                    self.selected_files.append(path)
                    self.file_listbox.insert(tk.END, f"  📄  {path.name}  —  {path.parent}")
            self.lbl_file_count.config(text=f"선택된 파일: {len(self.selected_files)}개")

    def clear_files(self):
        self.selected_files.clear()
        self.file_listbox.delete(0, tk.END)
        self.lbl_file_count.config(text="선택된 파일: 0개")
        self.btn_export.config(state=tk.DISABLED)
        self.current_summary = None
        self.lbl_rate_pill.config(text="실효 수수료율: 대기중", fg=NOTION_COLORS["ink-muted"])

    def run_settlement(self):
        if not self.selected_files:
            messagebox.showwarning("파일 필요", "정산할 엑셀 파일을 먼저 추가해 주세요.")
            return

        all_records = []
        self.txt_result.delete("1.0", tk.END)
        self.txt_result.insert(tk.END, "▶ 엑셀 데이터 분석 및 실효 수수료율 역산 중...\n\n")

        try:
            for file_path in self.selected_files:
                ch_name, records = SmartExcelSettlementProcessor.parse_excel_file(file_path)
                all_records.extend(records)
                self.txt_result.insert(
                    tk.END,
                    f" • [{ch_name}] {file_path.name} — {len(records)}건 감지\n"
                )

            if not all_records:
                messagebox.showerror("오류", "문서에서 유효한 거래 데이터를 찾을 수 없습니다.")
                return

            summary = SmartExcelSettlementProcessor.calculate_settlement(all_records)
            self.current_summary = summary

            total_deduction = summary["total_fee"] + summary["refund_offset"]
            self.card_sales.val_lbl.config(text=f"{int(summary['total_sales']):,}원")
            self.card_fees.val_lbl.config(text=f"{int(total_deduction):,}원")
            self.card_payout.val_lbl.config(text=f"{int(summary['final_payout']):,}원")

            self.lbl_rate_pill.config(
                text=f"● 전체 실효 수수료율: {summary['overall_rate_percent']:.2f}%",
                fg=NOTION_COLORS["primary"]
            )

            self.txt_result.insert(tk.END, "\n" + "─" * 60 + "\n")
            self.txt_result.insert(tk.END, f"  종합 정산 리포트 Summary (총 {summary['total_count']}건 처리)\n")
            self.txt_result.insert(tk.END, "─" * 60 + "\n")
            self.txt_result.insert(tk.END, f"  (+) 총 판매금액        : {int(summary['total_sales']):>12,} 원\n")
            self.txt_result.insert(tk.END, f"  (-) 공제 수수료        : {int(summary['total_fee']):>12,} 원 (실효 평균 {summary['overall_rate_percent']:.2f}%)\n")
            self.txt_result.insert(tk.END, f"  (+) 배송비 정산액      : {int(summary['total_shipping_fee']):>12,} 원\n")
            self.txt_result.insert(tk.END, f"  (-) 반품/환불 상계액   : {int(summary['refund_offset']):>12,} 원\n")
            self.txt_result.insert(tk.END, "─" * 60 + "\n")
            self.txt_result.insert(tk.END, f"  (=) 최종 실지급액      : {int(summary['final_payout']):>12,} 원\n")
            if summary["carryover_out"] > 0:
                self.txt_result.insert(tk.END, f"  (→) 익월 마이너스 이월 : {int(summary['carryover_out']):>12,} 원\n")
            self.txt_result.insert(tk.END, "─" * 60 + "\n\n")

            self.txt_result.insert(tk.END, "[채널별 실데이터 역산 분석]\n")
            for ch, d in summary["channel_breakdown"].items():
                self.txt_result.insert(
                    tk.END,
                    f"  • {ch:<14s} | 실효 요율 {d['effective_rate_percent']:>5.2f}% | {d['count']:>2}건 | 매출 {int(d['sales']):>9,}원 | 수수료 {int(d['fee']):>8,}원\n"
                )

            self.btn_export.config(state=tk.NORMAL)
            messagebox.showinfo("정산 완료", f"총 {summary['total_count']}건의 정산이 완료되었습니다.\n최종 실지급액: {int(summary['final_payout']):,}원")

        except Exception as e:
            messagebox.showerror("정산 오류", f"처리 중 오류가 발생했습니다:\n{str(e)}")

    def export_excel(self):
        if not self.current_summary:
            return

        default_name = f"Notion_Settlement_{self.current_summary['overall_rate_percent']}pct.xlsx"
        save_path = filedialog.asksaveasfilename(
            title="정산 보고서 저장 위치를 선택하세요",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if save_path:
            try:
                SmartExcelSettlementProcessor.export_settlement_excel(
                    self.current_summary,
                    Path(save_path)
                )
                messagebox.showinfo("저장 완료", f"정산 엑셀 보고서가 성공적으로 저장되었습니다.\n경로: {save_path}")
            except Exception as e:
                messagebox.showerror("저장 실패", f"파일 저장 중 오류가 발생했습니다:\n{str(e)}")

def main():
    root = tk.Tk()
    app = NotionSettlementApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
