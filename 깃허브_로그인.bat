@echo off
chcp 65001 > nul
title GitHub CLI 로그인

set "PATH=%LOCALAPPDATA%\Programs\GitHub CLI;%LOCALAPPDATA%\Programs\Git\cmd;%~dp0tools\bin;%~dp0tools\git\cmd;%PATH%"

echo ========================================================
echo  GitHub CLI 간편 웹 브라우저 로그인을 시작합니다.
echo ========================================================
echo.
echo 1. 콘솔에 8자리 인증 코드 (예: ABCD-1234) 가 출력됩니다.
echo 2. 엔터를 누르면 웹 브라우저가 자동으로 열립니다.
echo 3. 브라우저에 8자리 코드를 입력하고 [Authorize] 를 누르면 끝납니다!
echo.
echo ========================================================
echo.

gh auth login --hostname github.com --git-protocol https --web

echo.
echo ========================================================
gh auth status
echo ========================================================
echo 로그인이 완료되었습니다! 이 창을 닫고 '깃허브_업로드.bat'을 실행해 주세요.
pause
