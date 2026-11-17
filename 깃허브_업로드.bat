@echo off
chcp 65001 > nul
title GitHub 저장소 생성 및 코드 업로드

set "PATH=%~dp0tools\bin;%~dp0tools\git\cmd;%PATH%"

echo ========================================================
echo  GitHub 저장소 생성 및 푸시 (GitHub CLI)
echo ========================================================
echo.

:: 로그인 상태 체크
gh auth status > nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] 아직 GitHub에 로그인되지 않았습니다.
    echo 먼저 '깃허브_로그인.bat' 을 실행하여 로그인해 주세요.
    echo.
    pause
    exit /b 1
)

echo [1/3] 변경 사항 최종 커밋 확인...
git add .
git commit -m "feat: complete Notion settlement workspace" > nul 2>&1

echo [2/3] GitHub에 새 저장소 생성 중...
set /p REPO_NAME="생성할 GitHub 저장소 이름을 입력하세요 (기본: notion-settlement): "
if "%REPO_NAME%"=="" set REPO_NAME=notion-settlement

set /p IS_PUBLIC="공개 저장소(public)로 만들까요? (Y: 공개, N: 비공개) [Y/N, 기본 Y]: "
if /i "%IS_PUBLIC%"=="N" (
    set VISIBILITY=--private
) else (
    set VISIBILITY=--public
)

echo.
echo -> 저장소 이름: %REPO_NAME% (%VISIBILITY%)
echo.

gh repo create %REPO_NAME% %VISIBILITY% --source=. --remote=origin --push

echo.
echo ========================================================
echo  GitHub 업로드가 성공적으로 완료되었습니다!
echo ========================================================
gh repo view --web
pause
