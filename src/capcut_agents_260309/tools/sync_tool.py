from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, List
import os
import tempfile
import numpy as np
from scipy import signal
from scipy.io import wavfile
import imageio_ffmpeg
import subprocess

class SyncToolInput(BaseModel):
    """Sync 도구에 전달할 데이터의 형식입니다."""
    video_folder_path: str = Field(..., description="동기화를 맞출 영상 파일들이 들어있는 폴더의 절대 경로입니다.")

class SyncTool(BaseTool):
    name: str = "Video_Sync_Tool"
    description: str = (
        "지정된 폴더 내의 모든 영상 파일(.mp4, .mov)을 자동으로 찾아 오디오 파형을 분석하고, "
        "첫 번째 영상(알파벳 순 기준) 대비 나머지 영상들의 오디오 딜레이를 밀리초(ms) 단위로 계산합니다."
    )
    args_schema: Type[BaseModel] = SyncToolInput

    def _extract_audio_data(self, video_path: str, target_sr=8000) -> tuple[np.ndarray, int]:
        # (기존 코드와 동일)
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_wav = tempfile.mktemp(suffix=".wav")
        
        cmd = [
            ffmpeg_exe,
            "-i", video_path,
            "-t", "600",
            "-vn",
            "-ac", "1",
            "-ar", str(target_sr),
            "-y",
            temp_wav
        ]
        
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            sr, audio_array = wavfile.read(temp_wav)
            audio_array = audio_array.astype(np.float64)
            audio_array = audio_array - np.mean(audio_array)
            std = np.std(audio_array)
            if std > 0:
                audio_array = audio_array / std
            return audio_array, target_sr
        except subprocess.CalledProcessError as e:
            raise ValueError(f"ffmpeg 오디오 추출 실패: {e.stderr.decode('utf-8', errors='ignore')}")
        finally:
            if os.path.exists(temp_wav):
                os.remove(temp_wav)

    def _get_time_from_filename(self, filename: str) -> int:
        # (기존 코드와 동일)
        import re
        match = re.search(r'_(\d{2})(\d{2})(\d{2})', filename)
        if match:
            h, m, s = map(int, match.groups())
            return h * 3600 + m * 60 + s
        return 0

    def _calculate_delay(self, ref_audio: np.ndarray, target_audio: np.ndarray, sr: int, ref_name: str, target_name: str) -> float:
        # (기존 코드와 동일)
        if np.max(np.abs(ref_audio)) < 1e-6 or np.max(np.abs(target_audio)) < 1e-6:
            ref_time = self._get_time_from_filename(ref_name)
            target_time = self._get_time_from_filename(target_name)
            if ref_time > 0 and target_time > 0:
                diff_sec = target_time - ref_time
                return diff_sec * 1000.0
            else:
                raise ValueError("오디오가 무음이며 파일명에서 시간을 추출할 수 없습니다.")
        
        correlation = signal.correlate(ref_audio, target_audio, mode='full', method='fft')
        if np.max(np.abs(correlation)) < 1e-6:
            ref_time = self._get_time_from_filename(ref_name)
            target_time = self._get_time_from_filename(target_name)
            if ref_time > 0 and target_time > 0:
                diff_sec = target_time - ref_time
                return diff_sec * 1000.0
            
        lag = np.argmax(correlation)
        delay_samples = lag - (len(target_audio) - 1)
        delay_ms = (delay_samples / sr) * 1000.0
        return delay_ms

    def _run(self, video_folder_path: str) -> str:
        if not os.path.exists(video_folder_path):
            return f"오류: 폴더가 존재하지 않습니다: {video_folder_path}"

        # 폴더 내 영상 파일 스캔
        video_files = [f for f in os.listdir(video_folder_path) if f.lower().endswith(('.mp4', '.mov'))]
        video_files.sort() # 알파벳 순 정렬하여 기준점 일관성 유지
        
        if len(video_files) < 1:
            return "오류: 폴더 내에 영상 파일이 없습니다."
        
        video_paths = [os.path.join(video_folder_path, f) for f in video_files]

        if len(video_paths) < 2:
            return f"안내: 단일 영상({video_files[0]})입니다. 동기화가 필요 없습니다. (0ms)"

        try:
            ref_path = video_paths[0]
            ref_audio, sr = self._extract_audio_data(ref_path)
            
            import json
            results = {
                "reference": os.path.basename(ref_path),
                "offsets": {os.path.basename(ref_path): 0.0}
            }

            for target_path in video_paths[1:]:
                target_audio, _ = self._extract_audio_data(target_path, target_sr=sr)
                delay_ms = self._calculate_delay(
                    ref_audio, target_audio, sr, 
                    os.path.basename(ref_path), os.path.basename(target_path)
                )
                results["offsets"][os.path.basename(target_path)] = round(delay_ms, 2)

            return json.dumps(results, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"오류: 동기화 분석 중 문제가 발생했습니다: {str(e)}"
