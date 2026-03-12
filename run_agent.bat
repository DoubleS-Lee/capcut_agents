@echo off
chcp 65001 > nul
set PYTHONPATH=d:\00.Google CLI\capcut_agents_260309\src
.venv\Scripts\python.exe -m capcut_agents_260309.main run --cmd "가장 임팩트 있는 부분을 찾아서 1분짜리 영상으로 편집해줘"
