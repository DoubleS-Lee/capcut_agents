@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo.
    echo [오류] 가상환경이 없습니다.
    echo   먼저 설치.bat 을 실행하세요.
    echo.
    pause
    exit /b 1
)
.venv\Scripts\python.exe gui.py %*
