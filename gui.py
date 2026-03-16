#!/usr/bin/env python
"""
CapCut 리액션 편집 에이전트 - GUI
실행: uv run python gui.py
"""
import os
import sys

# CUDA DLL 경로 등록 — torch/ctranslate2 임포트 전에 반드시 실행
# _dll_dir_handles: GC 방지용 전역 보관 (os.add_dll_directory 반환값을 버리면 즉시 해제됨)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
import site as _site
_dll_dir_handles = []
for _sp in _site.getsitepackages():
    for _sub in [os.path.join("torch", "lib"), "ctranslate2"]:
        _p = os.path.join(_sp, _sub)
        if os.path.exists(_p):
            try:
                _dll_dir_handles.append(os.add_dll_directory(_p))
            except (AttributeError, OSError):
                pass
            if _p not in os.environ.get("PATH", ""):
                os.environ["PATH"] = _p + os.pathsep + os.environ["PATH"]
    for _pkg in ["cublas", "cudnn", "cusparse", "cufft", "curand", "nvrtc"]:
        _bin = os.path.join(_sp, "nvidia", _pkg, "bin")
        if os.path.exists(_bin):
            try:
                _dll_dir_handles.append(os.add_dll_directory(_bin))
            except (AttributeError, OSError):
                pass
            if _bin not in os.environ.get("PATH", ""):
                os.environ["PATH"] = _bin + os.pathsep + os.environ["PATH"]

import json
import threading
import subprocess
import time
import traceback

# Windows stdout 인코딩
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

# ──────────────────────────────────────────────
# 전역 설정
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# src/ 레이아웃 패키지를 Python 경로에 추가
_src_path = os.path.join(BASE_DIR, "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
DEFAULT_OUTPUT = os.path.join(BASE_DIR, "output")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ──────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


def save_env(env: dict):
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            lines = f.readlines()

    # 기존 키 업데이트 또는 새 키 추가
    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in env:
                new_lines.append(f"{k}={env[k]}\n")
                updated_keys.add(k)
                continue
        new_lines.append(line if line.endswith("\n") else line + "\n")

    for k, v in env.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    # 현재 프로세스에도 반영
    for k, v in env.items():
        os.environ[k] = v


def detect_gpu_status() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return f"GPU: {name}"
        return "CPU 모드 (STT 속도 느림)"
    except Exception:
        return "GPU 감지 불가"


# ──────────────────────────────────────────────
# 메인 앱
# ──────────────────────────────────────────────
class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("CapCut 리액션 편집 에이전트")
        self.geometry("1000x760")
        self.minsize(860, 640)
        self.configure(bg="#1a1a2e")

        self._env = load_env()
        self._video_paths: list[str] = []
        self._video_folder: str = ""
        self._speaker_var = ctk.StringVar(value="ALL")
        self._speakers: list[str] = []
        self._mcp_proc: subprocess.Popen | None = None
        self._output_dir = ctk.StringVar(value=self._env.get("CAPCUT_OUTPUT_DIR", DEFAULT_OUTPUT))
        self._running = False
        self._stt_data: str = ""  # STT 완료 후 저장, 편집 실행 시 사용
        self._device_var = ctk.StringVar(value="auto")

        self._build_ui()
        self._refresh_gpu_badge()

    # ── UI 구성 ──────────────────────────────
    def _build_ui(self):
        # 최상단 헤더
        header = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(header, text="CapCut 리액션 편집 에이전트",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=16, pady=10)

        self._gpu_badge = ctk.CTkLabel(header, text="GPU 확인 중...",
                                       font=ctk.CTkFont(size=12),
                                       fg_color="#2a2a4a", corner_radius=8,
                                       padx=10, pady=4)
        self._gpu_badge.pack(side="right", padx=16, pady=10)

        # 좌우 분할
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=8)

        left_outer = ctk.CTkFrame(body, width=300, fg_color="#16213e", corner_radius=10)
        left_outer.pack(side="left", fill="y", padx=(0, 8))
        left_outer.pack_propagate(False)
        left = ctk.CTkScrollableFrame(left_outer, fg_color="transparent", width=278)
        left.pack(fill="both", expand=True)

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

        # 하단 로그
        self._build_log()

    def _build_left(self, parent):
        pad = {"padx": 14, "pady": 6}

        # ── API 키 ──
        ctk.CTkLabel(parent, text="API 키 설정",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)

        ctk.CTkLabel(parent, text="Gemini API Key", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(4, 0))
        self._gemini_entry = ctk.CTkEntry(parent, placeholder_text="AIza...", width=260)
        self._gemini_entry.pack(padx=14, pady=(0, 4))
        self._gemini_entry.insert(0, self._env.get("GEMINI_API_KEY", ""))

        ctk.CTkLabel(parent, text="HuggingFace Token", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(4, 0))
        self._hf_entry = ctk.CTkEntry(parent, placeholder_text="hf_...", width=260)
        self._hf_entry.pack(padx=14, pady=(0, 4))
        self._hf_entry.insert(0, self._env.get("HUGGINGFACE_TOKEN", ""))

        ctk.CTkButton(parent, text="저장", width=260, height=30,
                      command=self._save_api_keys).pack(padx=14, pady=(0, 10))

        ctk.CTkFrame(parent, height=1, fg_color="#333355").pack(fill="x", padx=14, pady=4)

        # ── STT 디바이스 선택 ──
        ctk.CTkLabel(parent, text="STT 연산 장치",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(6, 4))
        ctk.CTkSegmentedButton(parent, values=["자동", "GPU (CUDA)", "CPU"],
                               variable=self._device_var,
                               width=260,
                               command=self._on_device_change).pack(padx=14, pady=(0, 6))
        self._device_info = ctk.CTkLabel(parent, text="",
                                         font=ctk.CTkFont(size=10), text_color="#aaaacc",
                                         wraplength=240, justify="left")
        self._device_info.pack(anchor="w", padx=14, pady=(0, 4))

        ctk.CTkFrame(parent, height=1, fg_color="#333355").pack(fill="x", padx=14, pady=4)

        # ── Output 폴더 ──
        ctk.CTkLabel(parent, text="감탄사 편집 결과 출력 폴더",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        ctk.CTkLabel(parent, text="STT 파일은 동영상 폴더에 생성됩니다",
                     font=ctk.CTkFont(size=10), text_color="#888899").pack(anchor="w", padx=14, pady=(0, 2))
        self._output_label = ctk.CTkLabel(parent, text=self._shorten(self._output_dir.get()),
                                          font=ctk.CTkFont(size=10), text_color="#aaaacc",
                                          wraplength=240, justify="left")
        self._output_label.pack(anchor="w", padx=14, pady=(0, 4))
        ctk.CTkButton(parent, text="폴더 선택", width=260, height=30,
                      command=self._pick_output).pack(padx=14, pady=(0, 10))

        ctk.CTkFrame(parent, height=1, fg_color="#333355").pack(fill="x", padx=14, pady=4)

        # ── 지시사항 ──
        ctk.CTkLabel(parent, text="편집 지시사항",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", **pad)
        self._cmd_box = ctk.CTkTextbox(parent, width=260, height=100, font=ctk.CTkFont(size=11))
        self._cmd_box.pack(padx=14, pady=(0, 6))
        self._cmd_box.insert("1.0", "모든 짧은 감탄사와 리액션을 빠짐없이 추출해줘")

        # 프리셋 버튼
        presets = [
            ("모든 리액션", "모든 짧은 감탄사와 리액션을 빠짐없이 추출해줘"),
            ("기쁨/환희", "기쁨, 환희, 감동의 감탄사와 리액션이 있는 장면을 편집해줘"),
        ]
        for label, cmd in presets:
            ctk.CTkButton(parent, text=label, width=260, height=26,
                          fg_color="#2a2a5a", hover_color="#3a3a7a",
                          font=ctk.CTkFont(size=11),
                          command=lambda c=cmd: self._set_cmd(c)).pack(padx=14, pady=2)

    def _build_right(self, parent):
        # ── 영상 입력 ──
        vid_frame = ctk.CTkFrame(parent, fg_color="#16213e", corner_radius=10)
        vid_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(vid_frame, text="영상 파일",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(10, 4))

        # 드래그앤드롭 영역
        drop_zone = ctk.CTkFrame(vid_frame, height=80, fg_color="#0f3460", corner_radius=8,
                                  border_width=2, border_color="#3a3a8a")
        drop_zone.pack(fill="x", padx=14, pady=(0, 6))
        drop_zone.pack_propagate(False)
        ctk.CTkLabel(drop_zone,
                     text="영상 파일(.mp4, .mov) 또는 폴더를 여기에 드래그하세요",
                     font=ctk.CTkFont(size=12), text_color="#8888bb").place(relx=0.5, rely=0.5, anchor="center")
        drop_zone.drop_target_register(DND_FILES)
        drop_zone.dnd_bind("<<Drop>>", self._on_drop)

        btn_row = ctk.CTkFrame(vid_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkButton(btn_row, text="파일 선택", width=140, height=30,
                      command=self._pick_files).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="폴더 선택", width=140, height=30,
                      command=self._pick_folder).pack(side="left")
        ctk.CTkButton(btn_row, text="목록 초기화", width=100, height=30,
                      fg_color="#4a1a1a", hover_color="#6a2a2a",
                      command=self._clear_videos).pack(side="right")

        self._video_list = ctk.CTkTextbox(vid_frame, height=80, font=ctk.CTkFont(size=11),
                                           state="disabled")
        self._video_list.pack(fill="x", padx=14, pady=(0, 10))

        # ── 화자 선택 (STT 후 활성화) ──
        self._spk_frame = ctk.CTkFrame(parent, fg_color="#16213e", corner_radius=10)
        self._spk_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(self._spk_frame, text="화자 선택 (STT 완료 후 활성화)",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=(10, 4))
        self._spk_inner = ctk.CTkFrame(self._spk_frame, fg_color="transparent")
        self._spk_inner.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(self._spk_inner, text="감탄사 편집 실행시 화자 목록이 표시됩니다.",
                     text_color="#666688", font=ctk.CTkFont(size=11)).pack(anchor="w")

        # ── 실행 버튼 (2개로 분리) ──
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.pack(fill="x", pady=(0, 4))

        self._stt_btn = ctk.CTkButton(ctrl, text="① STT 추출",
                                      height=46, font=ctk.CTkFont(size=14, weight="bold"),
                                      fg_color="#1a5a8a", hover_color="#2a7abf",
                                      command=self._on_stt_run)
        self._stt_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._run_btn = ctk.CTkButton(ctrl, text="② 감탄사 편집 실행",
                                      height=46, font=ctk.CTkFont(size=14, weight="bold"),
                                      fg_color="#1a6a2a", hover_color="#2a9a40",
                                      state="disabled",
                                      command=self._on_crew_run)
        self._run_btn.pack(side="left", fill="x", expand=True)

        self._progress = ctk.CTkProgressBar(parent, height=6)
        self._progress.pack(fill="x", pady=(4, 0))
        self._progress.set(0)

    def _build_log(self):
        log_frame = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        hdr = ctk.CTkFrame(log_frame, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(hdr, text="실행 로그", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        ctk.CTkButton(hdr, text="지우기", width=60, height=22,
                      fg_color="#2a2a4a", hover_color="#3a3a6a",
                      font=ctk.CTkFont(size=11),
                      command=self._clear_log).pack(side="right")

        self._log_box = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(family="Consolas", size=11),
                                        state="disabled")
        self._log_box.pack(fill="both", expand=True, padx=10, pady=(4, 10))

    # ── 이벤트 핸들러 ──────────────────────────
    def _refresh_gpu_badge(self):
        def _check():
            status = detect_gpu_status()
            color = "#1a5a1a" if "GPU:" in status else "#5a3a1a"
            self._gpu_badge.configure(text=status, fg_color=color)
        threading.Thread(target=_check, daemon=True).start()

    def _on_device_change(self, value: str):
        import torch
        if value == "GPU (CUDA)":
            if torch.cuda.is_available():
                os.environ["CAPCUT_FORCE_DEVICE"] = "cuda"
                self._device_info.configure(text=f"GPU: {torch.cuda.get_device_name(0)}", text_color="#44cc44")
            else:
                self._device_info.configure(text="CUDA 불가 — torch CPU 버전이 설치됨.\n터미널에서 'uv sync' 실행 후 재시작하세요.", text_color="#cc4444")
                os.environ.pop("CAPCUT_FORCE_DEVICE", None)
        elif value == "CPU":
            os.environ["CAPCUT_FORCE_DEVICE"] = "cpu"
            self._device_info.configure(text="CPU 모드 (STT 속도 느림)", text_color="#ccaa44")
        else:
            os.environ.pop("CAPCUT_FORCE_DEVICE", None)
            import torch
            if torch.cuda.is_available():
                self._device_info.configure(text=f"자동 → GPU: {torch.cuda.get_device_name(0)}", text_color="#44cc44")
            else:
                self._device_info.configure(text="자동 → CPU (CUDA 없음)", text_color="#ccaa44")

    def _save_api_keys(self):
        keys = {
            "GEMINI_API_KEY": self._gemini_entry.get().strip(),
            "HUGGINGFACE_TOKEN": self._hf_entry.get().strip(),
        }
        keys = {k: v for k, v in keys.items() if v}
        if keys:
            save_env(keys)
            self._log("API 키 저장 완료.")
        else:
            self._log("[경고] 입력된 API 키가 없습니다.")

    def _pick_output(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="출력 폴더 선택")
        if path:
            self._output_dir.set(path)
            self._output_label.configure(text=self._shorten(path))
            save_env({"CAPCUT_OUTPUT_DIR": path})
            self._log(f"출력 폴더 저장: {path}")

    def _set_cmd(self, cmd: str):
        self._cmd_box.delete("1.0", "end")
        self._cmd_box.insert("1.0", cmd)

    def _on_drop(self, event):
        raw = event.data
        # tkinterdnd2: 경로에 공백 있으면 {} 로 감싸짐
        paths = self.tk.splitlist(raw)
        for p in paths:
            p = p.strip("{}")
            self._add_path(p)

    def _pick_files(self):
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(
            title="영상 파일 선택",
            filetypes=[("영상 파일", "*.mp4 *.mov"), ("모든 파일", "*.*")]
        )
        for p in paths:
            self._add_path(p)

    def _pick_folder(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="영상 폴더 선택")
        if folder:
            self._add_path(folder)

    def _add_path(self, path: str):
        path = os.path.normpath(path)
        if os.path.isdir(path):
            videos = [os.path.join(path, f) for f in os.listdir(path)
                      if f.lower().endswith((".mp4", ".mov"))]
            if videos:
                self._video_folder = path
                for v in videos:
                    if v not in self._video_paths:
                        self._video_paths.append(v)
                self._log(f"폴더에서 영상 {len(videos)}개 추가: {path}")
            else:
                self._log(f"[경고] 폴더에 mp4/mov 파일 없음: {path}")
        elif path.lower().endswith((".mp4", ".mov")):
            if path not in self._video_paths:
                self._video_paths.append(path)
                self._video_folder = os.path.dirname(path)
        self._refresh_video_list()

    def _clear_videos(self):
        self._video_paths.clear()
        self._video_folder = ""
        self._refresh_video_list()

    def _refresh_video_list(self):
        self._video_list.configure(state="normal")
        self._video_list.delete("1.0", "end")
        for p in self._video_paths:
            self._video_list.insert("end", os.path.basename(p) + "\n")
        self._video_list.configure(state="disabled")

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    def _log(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        def _insert():
            self._log_box.configure(state="normal")
            self._log_box.insert("end", f"[{ts}] {msg}\n")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        self.after(0, _insert)

    # ── 실행 흐름 ──────────────────────────────
    def _on_stt_run(self):
        if self._running:
            return
        if not self._video_paths:
            self._log("[에러] 영상 파일을 먼저 선택하세요.")
            return

        self._save_api_keys()
        self._running = True
        self._stt_btn.configure(state="disabled", text="STT 추출 중...")
        self._run_btn.configure(state="disabled")
        self._progress.set(0)
        threading.Thread(target=self._run_stt_flow, daemon=True).start()

    def _run_stt_flow(self):
        try:
            self._log("=" * 50)
            self._log("[1/2] MCP 서버 확인 중...")
            self._ensure_mcp_server()
            self.after(0, lambda: self._progress.set(0.1))

            self._log("[2/2] STT 추출 중... (처음 실행 시 시간이 걸립니다)")
            stt_data, speaker_info = self._run_stt()
            self.after(0, lambda: self._progress.set(0.5))

            if not stt_data:
                self._log("[에러] STT 실패. 로그를 확인하세요.")
                return

            self._stt_data = stt_data
            self.after(0, lambda: self._show_speakers(speaker_info))
            self._log("[안내] 화자를 선택한 뒤 [② 감탄사 편집 실행] 버튼을 누르세요.")

        except Exception as e:
            self._log(f"[에러] {e}\n{traceback.format_exc()}")
        finally:
            self._running = False
            self.after(0, lambda: self._stt_btn.configure(state="normal", text="① STT 추출"))
            # 편집 버튼은 STT 성공 시에만 활성화
            if self._stt_data:
                self.after(0, lambda: self._run_btn.configure(state="normal"))

    def _on_crew_run(self):
        if self._running:
            return
        if not self._stt_data:
            self._log("[에러] STT를 먼저 실행하세요.")
            return

        self._running = True
        self._stt_btn.configure(state="disabled")
        self._run_btn.configure(state="disabled", text="편집 실행 중...")
        self._progress.set(0.5)
        threading.Thread(target=self._run_crew_flow, daemon=True).start()

    def _run_crew_flow(self):
        try:
            self._log("=" * 50)
            self._log("[감탄사 편집] 캡컷 프로젝트 생성 중...")
            self._run_crew(self._stt_data)
            self.after(0, lambda: self._progress.set(1.0))

            out = self._output_dir.get()
            self._log(f"[완료] 결과 폴더: {out}")
            self.after(0, lambda: self._open_output(out))

        except Exception as e:
            self._log(f"[에러] {e}\n{traceback.format_exc()}")
        finally:
            self._running = False
            self.after(0, lambda: self._stt_btn.configure(state="normal"))
            self.after(0, lambda: self._run_btn.configure(state="normal", text="② 감탄사 편집 실행"))

    def _ensure_mcp_server(self):
        import socket
        try:
            with socket.create_connection(("127.0.0.1", 9000), timeout=1):
                self._log("MCP 서버 이미 실행 중.")
                return
        except OSError:
            pass

        self._log("MCP 서버 시작 중...")
        self._mcp_proc = subprocess.Popen(
            [sys.executable, os.path.join(BASE_DIR, "mcp_server.py")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        for _ in range(20):
            time.sleep(0.5)
            try:
                with socket.create_connection(("127.0.0.1", 9000), timeout=1):
                    self._log("MCP 서버 시작 완료.")
                    return
            except OSError:
                pass
        self._log("[경고] MCP 서버 응답 없음. 계속 진행합니다.")

    def _run_stt(self):
        first_video = self._video_paths[0]
        video_name = os.path.splitext(os.path.basename(first_video))[0]
        stt_path = os.path.join(self._video_folder, f"{video_name}_stt.json")

        if os.path.exists(stt_path):
            self._log(f"기존 STT 파일 사용: {os.path.basename(stt_path)}")
            with open(stt_path, encoding="utf-8") as f:
                raw = f.read()
            return self._parse_stt(raw)

        # 첫 번째 영상으로 STT
        import torch
        force = os.environ.get("CAPCUT_FORCE_DEVICE", "")
        if force == "cuda":
            self._log("[STT] 연산 장치: GPU (CUDA 강제)")
        elif force == "cpu":
            self._log("[STT] 연산 장치: CPU (강제 설정)")
        elif torch.cuda.is_available():
            self._log(f"[STT] 연산 장치: CUDA 자동 감지 (GPU: {torch.cuda.get_device_name(0)})")
        else:
            self._log("[STT] 연산 장치: CPU (CUDA 없음 — STT 속도가 느립니다)")

        # crewai를 stt_tool보다 먼저 완전히 초기화 (나중에 crew 실행 시 모듈 깨짐 방지)
        from crewai import Agent, Crew, Process, Task  # noqa
        from capcut_agents_260309.tools.stt_tool import STTTool
        tool = STTTool()
        self._log(f"STT 실행: {os.path.basename(first_video)}")
        raw = tool._run(first_video)

        # 에러 JSON 체크
        try:
            check = json.loads(raw)
            if "error" in check:
                raise RuntimeError(check["error"])
        except (json.JSONDecodeError, KeyError):
            pass

        with open(stt_path, "w", encoding="utf-8") as f:
            f.write(raw)
        self._log(f"STT 완료. {os.path.basename(stt_path)} 저장됨.")
        return self._parse_stt(raw)

    def _parse_stt(self, raw: str):
        try:
            data = json.loads(raw)
            speaker_info: dict[str, dict] = {}  # {spk: {first_time, samples, count}}
            for seg in data.get("segments", []):
                spk = seg.get("speaker", "UNKNOWN")
                text = seg.get("text", "").strip()
                start = seg.get("start", 0)
                if spk not in speaker_info:
                    speaker_info[spk] = {"first_time": start, "samples": [], "count": 0}
                speaker_info[spk]["count"] += 1
                if len(speaker_info[spk]["samples"]) < 3:
                    speaker_info[spk]["samples"].append(text)
            speakers = sorted(speaker_info.keys())
            self._log(f"감지된 화자: {', '.join(speakers) or '없음'}")
            return raw, speaker_info
        except Exception as e:
            self._log(f"[경고] STT 파싱 오류: {e}")
            return raw, {}

    def _show_speakers(self, speaker_info: dict):
        for w in self._spk_inner.winfo_children():
            w.destroy()

        self._speaker_var.set("ALL")

        def fmt_time(sec):
            m, s = divmod(int(sec), 60)
            return f"{m:02d}:{s:02d}"

        total = sum(i["count"] for i in speaker_info.values()) or 1
        speakers_sorted = sorted(speaker_info.keys())

        # 2열 그리드
        for i in range(0, len(speakers_sorted), 2):
            row = ctk.CTkFrame(self._spk_inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            row.columnconfigure(0, weight=1)
            row.columnconfigure(1, weight=1)

            for col, spk in enumerate(speakers_sorted[i:i+2]):
                info = speaker_info[spk]
                first_time = fmt_time(info["first_time"])
                pct = round(info["count"] / total * 100)
                samples = "\n".join(f"· {t}" for t in info["samples"])

                frame = ctk.CTkFrame(row, fg_color="#1e2a3a", corner_radius=6)
                frame.grid(row=0, column=col, padx=(0 if col == 0 else 4, 0), sticky="nsew")

                ctk.CTkRadioButton(frame, text=f"{spk}  {pct}%",
                                   variable=self._speaker_var, value=spk,
                                   font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=8, pady=(6, 2))
                ctk.CTkLabel(frame, text=f"첫 발화 {first_time}",
                             text_color="#8888bb", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10, pady=(0, 2))
                ctk.CTkLabel(frame, text=samples, text_color="#ccccdd",
                             font=ctk.CTkFont(size=12), wraplength=180, justify="left").pack(anchor="w", padx=10, pady=(0, 8))

        # 모든 화자 옵션
        ctk.CTkRadioButton(self._spk_inner, text="모든 화자",
                           variable=self._speaker_var, value="ALL").pack(anchor="w", pady=(6, 2))


    def _run_crew(self, stt_data: str):
        if self._video_paths:
            video_name = os.path.splitext(os.path.basename(self._video_paths[0]))[0]
            os.environ["CAPCUT_VIDEO_NAME"] = video_name

        from capcut_agents_260309.main import run_programmatic
        run_programmatic(
            video_folder=self._video_folder,
            cmd=self._cmd_box.get("1.0", "end").strip(),
            selected_speaker=self._speaker_var.get(),
            output_dir=self._output_dir.get(),
            stt_data=stt_data,
            video_paths=list(self._video_paths),
            progress_cb=self._log,
        )

    def _open_output(self, path: str):
        if os.path.isdir(path):
            os.startfile(path)

    # ── 헬퍼 ──────────────────────────────────
    def _shorten(self, path: str, max_len: int = 38) -> str:
        return path if len(path) <= max_len else "..." + path[-(max_len - 3):]

    def on_close(self):
        if self._mcp_proc:
            self._mcp_proc.terminate()
        self.destroy()


# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
