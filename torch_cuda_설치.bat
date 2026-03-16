@echo off
cd /d "%~dp0"
echo 모든 Python 프로세스를 종료합니다...
taskkill /f /im python.exe 2>nul
taskkill /f /im python3.exe 2>nul
timeout /t 2 /nobreak >nul

echo torch + torchaudio CUDA 버전 설치 중...
uv pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
echo 완료. 실행.bat 으로 GUI를 시작하세요.
pause
