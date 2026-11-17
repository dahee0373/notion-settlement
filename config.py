import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 데이터베이스 설정 (기본 SQLite, 운영 시 환경변수로 변경 가능)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'settlement.db'}")

# RPA 다운로드 임시/저장 폴더
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# 샘플 데이터 디렉토리
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
SAMPLE_DATA_DIR.mkdir(exist_ok=True)
