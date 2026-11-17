@echo off
chcp 65001 > nul
title 온라인 매출 정산 자동화 프로그램

echo ========================================================
echo  온라인 매출 정산 자동화 프로그램을 실행합니다...
echo ========================================================

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe app_gui.py
) else (
    python app_gui.py
)

pause
