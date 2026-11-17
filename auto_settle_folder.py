"""
폴더 기반 자동 정산 배치 스크립트:
input_excels 폴더의 모든 엑셀 파일을 읽어
엑셀에 기록된 실제 수수료를 1원 단위까지 스스로 분석/역산하여
output_settlement 폴더에 '온라인_매출정산보고서.xlsx'를 자동 생성합니다.
"""
from pathlib import Path
from datetime import datetime
from excel_settlement_processor import SmartExcelSettlementProcessor

def main():
    input_dir = Path("input_excels")
    output_dir = Path("output_settlement")
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    excel_files = list(input_dir.glob("*.xlsx")) + list(input_dir.glob("*.xls"))

    if not excel_files:
        print(f"[안내] '{input_dir}' 폴더에 엑셀 파일이 없습니다.")
        print("샘플 엑셀 파일들을 복사해 넣습니다...")
        sample_dir = Path("sample_excels")
        for s in sample_dir.glob("*.xlsx"):
            import shutil
            shutil.copy(s, input_dir / s.name)
        excel_files = list(input_dir.glob("*.xlsx"))

    print(f"=== 엑셀 파일 무설정 자동 정산 시작 (총 {len(excel_files)}개 파일) ===")
    all_records = []
    for f in excel_files:
        ch_name, records = SmartExcelSettlementProcessor.parse_excel_file(f)
        all_records.extend(records)
        print(f" - [{ch_name}] {f.name} -> {len(records)}건 분석 완료")

    # [핵심] 사용자가 수수료율을 전혀 주지 않아도 엑셀 파일 보고 스스로 알아냄!
    summary = SmartExcelSettlementProcessor.calculate_settlement(all_records)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"온라인_매출정산보고서_{timestamp}.xlsx"
    SmartExcelSettlementProcessor.export_settlement_excel(summary, output_file)

    print("\n" + "=" * 65)
    print(" [엑셀 실데이터 기반 자동 정산 요약]")
    print("=" * 65)
    print(f" * 총 주문건수   : {summary['total_count']} 건")
    print(f" * 총 판매금액   : {int(summary['total_sales']):,} 원")
    print(f" * 총 공제수수료 : {int(summary['total_fee']):,} 원 (전체 실효 평균: {summary['overall_rate_percent']:.2f}%)")
    print(f" * 배송비 정산액 : {int(summary['total_shipping_fee']):,} 원")
    print(f" * 환불 상계액   : {int(summary['refund_offset']):,} 원")
    print("-" * 65)
    print(f" ★ 최종 실지급액 : {int(summary['final_payout']):,} 원")
    print("=" * 65)

    print("\n[플랫폼별 엑셀 실데이터 자동 역산 분석]")
    for ch, d in summary["channel_breakdown"].items():
        print(f" * {ch:<16s} (실효 수수료율: {d['effective_rate_percent']:>5.2f}%) | {d['count']:>2}건 | 매출 {int(d['sales']):>9,}원 | 수수료 {int(d['fee']):>8,}원")

    print(f"\n[성공] 정산 보고서 엑셀이 생성되었습니다: {output_file.resolve()}")

if __name__ == "__main__":
    main()
