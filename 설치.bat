@echo off
cd /d "%~dp0"
echo.
echo ============================================
echo   CapCut Agents - 최초 설치 (설치.bat)
echo ============================================
echo.

:: 1. uv 설치 확인
where uv >nul 2>&1
if errorlevel 1 (
    echo [1/3] uv 가 없습니다. 설치 중...
    pip install uv
    if errorlevel 1 (
        echo.
        echo [오류] pip 으로 uv 설치 실패.
        echo   수동 설치: https://docs.astral.sh/uv/getting-started/installation/
        echo   설치 후 이 파일을 다시 실행하세요.
        pause
        exit /b 1
    )
)
echo [1/3] uv 확인 완료

:: 2. 가상환경 및 패키지 설치
echo [2/3] 패키지 설치 중... (처음 실행 시 수 분 소요)
uv sync
if errorlevel 1 (
    echo.
    echo [오류] 패키지 설치 실패. 위 오류 메시지를 확인하세요.
    pause
    exit /b 1
)
echo [2/3] 패키지 설치 완료

:: 3. .env 파일 생성
if not exist .env (
    echo [3/3] .env 파일 생성 중...
    copy .env.example .env >nul
    echo [3/3] .env 파일 생성 완료
) else (
    echo [3/3] .env 파일 이미 존재 - 건너뜀
)

echo.
echo ============================================
echo   설치 완료!
echo.
echo   [다음 단계]
echo.
echo   1. .env 파일에 API 키 입력 (필수)
echo      - GEMINI_API_KEY  : https://aistudio.google.com/
echo      - HUGGINGFACE_TOKEN: https://huggingface.co/settings/tokens
echo        (pyannote/speaker-diarization-3.1 모델 사용 동의 필요)
echo        https://huggingface.co/pyannote/speaker-diarization-3.1
echo.
echo   2. GPU 가속 설치 (선택사항 - NVIDIA GPU 있을 때만)
echo      torch_cuda_설치.bat 실행
echo.
echo   3. 실행.bat 으로 프로그램 시작
echo ============================================
echo.
pause
