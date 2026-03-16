# CapCut Agents - 감탄사 리액션 하이라이트 편집기

AI 에이전트가 영상에서 화자의 감탄사·리액션 구간을 자동으로 찾아 CapCut 프로젝트로 만들어주는 도구입니다.

---

## 사전 요구사항

- **Python 3.10 ~ 3.13** ([python.org](https://www.python.org/downloads/))
- **CapCut PC 버전** 설치
- **NVIDIA GPU** (선택사항 — 없으면 CPU로 동작, STT 속도 느림)

---

## 설치 (최초 1회)

### 1단계: 프로젝트 다운로드
```bash
git clone https://github.com/DoubleS-Lee/capcut_agents.git
cd capcut_agents
```
또는 ZIP으로 다운로드 후 압축 해제

### 2단계: 설치.bat 실행
`설치.bat` 을 더블클릭하면 자동으로:
- uv (패키지 관리자) 설치
- 가상환경 생성 및 패키지 설치
- `.env` 파일 생성

### 3단계: API 키 입력
`.env` 파일을 메모장으로 열어 입력:

```
GEMINI_API_KEY=여기에_키_입력
HUGGINGFACE_TOKEN=여기에_토큰_입력
```

- **Gemini API 키**: [Google AI Studio](https://aistudio.google.com/) → Get API key
- **HuggingFace 토큰**: [HuggingFace 설정](https://huggingface.co/settings/tokens) → New token (read 권한)
  - 추가로 아래 모델 사용 동의 필요 (로그인 후 페이지에서 동의 버튼 클릭):
  - [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1)
  - [pyannote/segmentation-3.0](https://huggingface.co/pyannote/segmentation-3.0)

### 4단계: GPU 가속 설치 (선택사항, NVIDIA GPU 전용)
`torch_cuda_설치.bat` 을 더블클릭

---

## 실행

`실행.bat` 을 더블클릭

---

## 사용 방법

1. **영상 추가** — 파일을 드래그앤드롭하거나 [파일 선택] 버튼 사용
2. **① STT 추출** 버튼 클릭 — 영상에서 대사를 텍스트로 변환 (수 분 소요)
3. **화자 선택** — 추출된 화자 목록에서 원하는 화자 선택
4. **편집 지시사항** 입력 (예: "모든 리액션", "웃음과 감탄사만")
5. **② 감탄사 편집 실행** 버튼 클릭
6. CapCut을 재시작하면 홈 화면에 새 프로젝트가 나타남

---

## 폴더 구조

```
capcut_agents/
├── 설치.bat              # 최초 설치
├── 실행.bat              # 프로그램 시작
├── torch_cuda_설치.bat   # GPU 가속 설치 (선택)
├── gui.py               # GUI 메인
├── mcp_server.py        # CapCut 프로젝트 생성 서버
├── .env                 # API 키 설정 (git 미포함)
├── .env.example         # .env 템플릿
├── reference/           # CapCut 프로젝트 템플릿
└── src/capcut_agents_260309/
    ├── config/
    │   ├── agents.yaml  # AI 에이전트 설정
    │   └── tasks.yaml   # 작업 정의
    └── tools/
        └── stt_tool.py  # STT + 화자 분리 도구
```
