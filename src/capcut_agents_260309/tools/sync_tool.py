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
    video_paths: List[str] = Field(..., description="동기화를 맞출 영상 파일들의 절대 경로 리스트입니다. 첫 번째 영상이 기준 영상이 됩니다.")

class SyncTool(BaseTool):
    name: str = "Video_Sync_Tool"
    description: str = (
        "다중 카메라 영상들의 오디오 파형을 분석하여, 첫 번째 영상(기준) 대비 나머지 영상들의 오디오 딜레이를 밀리초(ms) 단위로 계산합니다. "
        "반드시 2개 이상의 영상 경로 리스트를 입력해야 합니다."
    )
    args_schema: Type[BaseModel] = SyncToolInput

    def _extract_audio_data(self, video_path: str, target_sr=8000) -> tuple[np.ndarray, int]:
        """ffmpeg 바이너리를 사용하여 영상에서 처음 10분(600초) 분량의 오디오만 추출하고 numpy 배열로 변환 (모노 변환 포함)"""
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_wav = tempfile.mktemp(suffix=".wav")
        
        cmd = [
            ffmpeg_exe,
            "-i", video_path,
            "-t", "600",        # 처음 10분(600초)
            "-vn",              # 비디오 비활성화
            "-ac", "1",         # 모노
            "-ar", str(target_sr), # 샘플 레이트
            "-y",               # 덮어쓰기
            temp_wav
        ]
        
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            sr, audio_array = wavfile.read(temp_wav)
            
            # audio_array가 정수형일 수 있으므로 float로 변환
            audio_array = audio_array.astype(np.float64)
            
            # DC 오프셋 제거 및 정규화 (Peak 오류 방지)
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
        """파일명에서 시간(HHMMSS)을 추출하여 초 단위로 변환합니다."""
        import re
        # YYYYMMDD_HHMMSS 형태에서 HHMMSS 추출
        match = re.search(r'_(\d{2})(\d{2})(\d{2})', filename)
        if match:
            h, m, s = map(int, match.groups())
            return h * 3600 + m * 60 + s
        return 0

    def _calculate_delay(self, ref_audio: np.ndarray, target_audio: np.ndarray, sr: int, ref_name: str, target_name: str) -> float:
        """두 오디오 배열 간의 시간 오차(delay)를 계산 (밀리초 단위)"""
        
        # 오디오가 완전히 무음(std가 0)인지 확인
        if np.max(np.abs(ref_audio)) < 1e-6 or np.max(np.abs(target_audio)) < 1e-6:
            # 오디오가 없으므로 파일명 메타데이터 기반으로 차이 계산
            ref_time = self._get_time_from_filename(ref_name)
            target_time = self._get_time_from_filename(target_name)
            if ref_time > 0 and target_time > 0:
                diff_sec = target_time - ref_time
                print(f"[경고] {target_name}의 오디오 파형 분석에 실패(무음 또는 손상)하여 파일명 시간 기반으로 계산했습니다.")
                return diff_sec * 1000.0
            else:
                raise ValueError("오디오가 무음이며 파일명에서 시간을 추출할 수 없습니다.")
        
        # 상호상관도 계산 (고속 푸리에 변환(FFT) 사용으로 연산 속도 극대화)
        correlation = signal.correlate(ref_audio, target_audio, mode='full', method='fft')
        
        # 유효한 Peak가 없는 경우 (모두 0에 가까움)
        if np.max(np.abs(correlation)) < 1e-6:
            ref_time = self._get_time_from_filename(ref_name)
            target_time = self._get_time_from_filename(target_name)
            if ref_time > 0 and target_time > 0:
                diff_sec = target_time - ref_time
                print(f"[경고] {target_name}의 유효한 오디오 파형 매칭점(Peak)을 찾지 못해 파일명 시간 기반으로 계산했습니다.")
                return diff_sec * 1000.0
            
        # 가장 일치하는 지점(Peak)의 인덱스 찾기
        lag = np.argmax(correlation)
        
        # 지연 샘플 수 계산
        delay_samples = lag - (len(target_audio) - 1)
        
        # 밀리초(ms) 단위로 변환
        delay_ms = (delay_samples / sr) * 1000.0
        
        return delay_ms

    def _run(self, video_paths: List[str]) -> str:
        if len(video_paths) < 2:
            return "오류: 비교할 영상이 2개 이상 필요합니다."

        for path in video_paths:
            if not os.path.exists(path):
                return f"오류: 파일이 존재하지 않습니다: {path}"

        try:
            ref_path = video_paths[0]
            # 1. 기준 영상 오디오 추출
            ref_audio, sr = self._extract_audio_data(ref_path)
            
            results = []
            results.append(f"기준 영상: {os.path.basename(ref_path)} (0ms)")

            # 2. 나머지 영상들과 비교
            for target_path in video_paths[1:]:
                target_audio, _ = self._extract_audio_data(target_path, target_sr=sr)
                
                # 딜레이 계산
                delay_ms = self._calculate_delay(
                    ref_audio, target_audio, sr, 
                    os.path.basename(ref_path), os.path.basename(target_path)
                )
                
                # 양수: target이 ref보다 먼저 시작됨 (target을 뒤로 밀어야 함)
                # 음수: target이 ref보다 늦게 시작됨 (target을 앞으로 당겨야 함)
                results.append(f"대상 영상: {os.path.basename(target_path)} -> 딜레이: {delay_ms:.2f} ms")

            return "\\n".join(results)

        except Exception as e:
            return f"오류: 동기화 분석 중 문제가 발생했습니다: {str(e)}"
