# Notion Settlement Workspace (온라인 매출 정산)

[DESIGN-notion.md](file:///c:/Users/dahee.hong/Downloads/DESIGN-notion.md)의 노션 공식 디자인 시스템(Notion Design Language System)을 100% 적용한 온라인 다채널 매출 정산 프로그램입니다.

---

## 1. 적용된 노션 디자인 시스템 핵심 사양

* **Canvas & Surface**:
  * 차가운 흰색 대신 눈이 편안한 시그니처 웜 페이퍼 캔버스(`canvas-soft`: `#f6f5f4`)를 기본 배경으로 채택.
  * 카드는 순백의 서피스(`surface`: `#ffffff`)와 1px 얇은 헤어라인 테두리(`hairline`: `#e6e6e6`)로 우아하게 분리.
* **Colors & Hero Night Band**:
  * 상단 헤더에 노션의 시그니처 나이트 밴드(`secondary`: `#213183`) 적용.
  * 오직 주요 실행 액션(CTA)과 링크에만 노션 블루(`primary`: `#0075de`, 호버 `#005bab`)를 집중 배치.
  * 스티커 팰릿(`accent-sky`: `#62aef0`, `accent-orange`: `#dd5b00`, `accent-green`: `#1aae39` 등)을 상태 태그와 뱃지에만 섬세하게 사용.
* **Typography**:
  * `NotionInter` / `Segoe UI` 기반으로 대담한 굵기의 헤드라인(Bold 700)과 차분한 바디(Regular 400)의 명확한 위계 구축.
* **Zero-Config (엑셀 수수료 자동 역산)**:
  * 사람이 수수료율 숫자를 입력할 필요 없이, 엑셀 파일 내의 실제 결제액/수수료/정산액을 스스로 분석하여 1원 단위까지 완벽하게 정산.

---

## 2. 실행 방법 (2가지 모드 지원)

### [모드 1] 윈도우 데스크톱 프로그램 실행
* **[정산프로그램_실행.bat](file:///c:/Users/dahee.hong/Desktop/새폴더/정산프로그램_실행.bat)** 더블 클릭!
* 노션 테마가 완벽 적용된 독립형 데스크톱 창이 실행됩니다.

### [모드 2] 브라우저 드래그앤드롭 웹 워크스페이스 실행
* **[노션_웹정산_실행.bat](file:///c:/Users/dahee.hong/Desktop/새폴더/노션_웹정산_실행.bat)** 더블 클릭! (또는 [notion_web.html](file:///c:/Users/dahee.hong/Desktop/새폴더/notion_web.html) 열기)
* 크롬/엣지 브라우저에서 노션 특유의 감성적인 폰트, 미려한 섀도우, 마우스 드래그앤드롭 엑셀 업로드와 인터랙티브 리포트를 즐기실 수 있습니다.

---

## 3. 핵심 파일 목록

- [app_gui.py](file:///c:/Users/dahee.hong/Desktop/새폴더/app_gui.py): 노션 디자인 시스템 적용 데스크톱 GUI
- [notion_web.html](file:///c:/Users/dahee.hong/Desktop/새폴더/notion_web.html): 노션 디자인 토큰 100% 웹 드래그앤드롭 워크스페이스
- [excel_settlement_processor.py](file:///c:/Users/dahee.hong/Desktop/새폴더/excel_settlement_processor.py): 노션 서식 엑셀 출력 엔진
- [정산프로그램_실행.bat](file:///c:/Users/dahee.hong/Desktop/새폴더/정산프로그램_실행.bat): 데스크톱 앱 더블 클릭 실행 파일
- [노션_웹정산_실행.bat](file:///c:/Users/dahee.hong/Desktop/새폴더/노션_웹정산_실행.bat): 웹 워크스페이스 더블 클릭 실행 파일
- `sample_excels/`: 바로 테스트할 수 있는 스마트스토어/쿠팡 샘플 엑셀 파일
- `output_settlement/`: 노션 서식으로 생성된 정산 보고서 엑셀 저장소
