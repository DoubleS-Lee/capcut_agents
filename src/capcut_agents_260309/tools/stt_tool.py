import os

# OpenMP 중복 로드 시 강제 종료되는 버그 방지
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# CUDA DLL 경로 등록 (핸들을 모듈 전역에 보관해야 GC 해제 방지됨)
import site
_dll_dir_handles = []
for sp in site.getsitepackages():
    for sub in [os.path.join('torch', 'lib'), 'ctranslate2']:
        p = os.path.join(sp, sub)
        if os.path.exists(p):
            try:
                _dll_dir_handles.append(os.add_dll_directory(p))
            except (AttributeError, OSError):
                pass
            if p not in os.environ.get('PATH', ''):
                os.environ['PATH'] = p + os.pathsep + os.environ['PATH']
    for pkg in ['cublas', 'cudnn', 'cusparse', 'cufft', 'curand', 'nvrtc']:
        b = os.path.join(sp, 'nvidia', pkg, 'bin')
        if os.path.exists(b):
            try:
                _dll_dir_handles.append(os.add_dll_directory(b))
            except (AttributeError, OSError):
                pass
            if b not in os.environ.get('PATH', ''):
                os.environ['PATH'] = b + os.pathsep + os.environ['PATH']

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import os
from moviepy import VideoFileClip
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
import torch
import warnings

# Pyannote 화자 분리 중 발생하는 PyTorch UserWarning(std(): degrees of freedom is <= 0) 무시
warnings.filterwarnings("ignore", message=".*degrees of freedom is <= 0.*")

class STTToolInput(BaseModel):
    """STT 도구에 전달할 데이터의 형식입니다."""
    video_path: str = Field(..., description="텍스트로 변환할 원본 영상(.mp4, .mov 등)의 절대 또는 상대 경로입니다.")

# 글로벌 캐시로 선언하여 함수가 종료될 때 모델 인스턴스가 파괴(C++ Destructor 호출)되며 강제 종료되는 버그 방지
_whisper_model_cache = None
_diarization_pipeline_cache = None

class STTTool(BaseTool):
    name: str = "Video_STT_Tool"
    description: str = (
        "이 도구는 영상 파일에서 오디오를 추출하고, 화자 분리(Speaker Diarization) 기술을 적용하여 "
        "누가 언제 무슨 말을 했는지 텍스트(대본)로 변환해 줍니다. "
        "결과물은 JSON 형식(start, end, speaker, text 등)으로 반환되어 대화 편집에 매우 유용합니다."
    )
    args_schema: Type[BaseModel] = STTToolInput

    def _run(self, video_path: str) -> str:
        global _whisper_model_cache, _diarization_pipeline_cache

        if not os.path.exists(video_path):
            import json
            return json.dumps({"error": f"파일이 존재하지 않습니다. 경로를 확인하세요: {video_path}"}, ensure_ascii=False)

        try:
            # 1. 임시 폴더에 오디오 파일(.wav) 추출
            print("[STT] 1. 오디오 추출 시작...", flush=True)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            audio_path = os.path.join(os.path.dirname(video_path), f"{video_name}.wav")
            
            with VideoFileClip(video_path) as video:
                audio = video.audio
                if audio is None:
                    import json
                    return json.dumps({"error": f"영상에 오디오 트랙이 존재하지 않습니다. ({video_path})"}, ensure_ascii=False)
                # 로그 출력을 줄이기 위해 logger=None 설정
                audio.write_audiofile(audio_path, codec='pcm_s16le', logger=None)

            print("[STT] 2. 모델 로딩 (Whisper + Diarization)...", flush=True)
            # 2. 모델 로드
            if _whisper_model_cache is None:
                force = os.environ.get("CAPCUT_FORCE_DEVICE", "")
                if force in ("cuda", "cpu"):
                    device = force
                else:
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
                print(f"[STT] 디바이스: {device} / 연산 타입: {compute_type}", flush=True)
                _whisper_model_cache = WhisperModel("base", device=device, compute_type=compute_type)
            model = _whisper_model_cache

            if _diarization_pipeline_cache is None:
                # pyannote.audio 파이프라인 로드 (HuggingFace 토큰 불필요 모델 혹은 미리 수락된 토큰 셋팅 권장)
                # 화자 분리 기본 모델 로드
                try:
                    # Note: pyannote.audio 3.1.1 requires a huggingface token for the speaker diarization pipeline
                    # If this fails, it's likely due to missing auth. We will fallback to Whisper only if it fails.
                    hf_token = os.getenv("HUGGINGFACE_TOKEN") # 또는 사용자에게 토큰 요청 필요
                    if hf_token:
                        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=hf_token)
                        if torch.cuda.is_available():
                            pipeline.to(torch.device("cuda"))
                        _diarization_pipeline_cache = pipeline
                    else:
                        print("[STT] 주의: HUGGINGFACE_TOKEN 환경 변수가 없어 화자 분리 모델을 로드할 수 없습니다. 화자 분리 기능이 비활성화됩니다.", flush=True)
                except Exception as e:
                    print(f"[STT] 화자 분리 모델 로드 중 오류 발생 (Whisper 단독으로 진행): {e}", flush=True)

            print("[STT] 3. 자막 변환(transcribe) 및 화자 분리 시작...", flush=True)
            
            # Whisper STT
            segments, info = model.transcribe(audio_path, beam_size=5, language="ko")
            whisper_segments = list(segments)
            
            diarization_result = None
            if _diarization_pipeline_cache:
                print("[STT] 화자 분리 분석 중...", flush=True)
                # pyannote 4.x는 torchcodec으로 파일을 직접 읽으려 해서 실패함
                # → scipy로 WAV 직접 로드 후 waveform dict 전달로 우회
                from scipy.io import wavfile
                sample_rate, wav_np = wavfile.read(audio_path)
                if wav_np.ndim == 1:
                    wav_np = wav_np[None, :]          # (1, samples)
                else:
                    wav_np = wav_np.T                 # (channels, samples)
                waveform = torch.from_numpy(wav_np.astype("float32") / 32768.0)
                diarization_result = _diarization_pipeline_cache(
                    {"waveform": waveform, "sample_rate": sample_rate}
                )
                
                # pyannote.audio v4.0 이상에서는 DiarizeOutput 객체를 반환하므로 내부 Annotation 객체로 변환
                if hasattr(diarization_result, "speaker_diarization"):
                    diarization_result = diarization_result.speaker_diarization

            import json
            result_data = {
                "file": os.path.basename(video_path),
                "language": info.language,
                "segments": []
            }

            print("[STT] 4. 데이터 병합 중...", flush=True)
            
            if diarization_result:
                # 화자 분리 결과와 Whisper 결과를 맵핑
                for segment in whisper_segments:
                    speaker = "UNKNOWN"
                    max_intersection = 0.0
                    
                    # 가장 많이 겹치는 화자 찾기
                    for turn, _, spk in diarization_result.itertracks(yield_label=True):
                        intersection = max(0, min(segment.end, turn.end) - max(segment.start, turn.start))
                        if intersection > max_intersection:
                            max_intersection = intersection
                            speaker = spk
                            
                    result_data["segments"].append({
                        "start": round(segment.start, 3),
                        "end": round(segment.end, 3),
                        "speaker": speaker,
                        "text": segment.text.strip()
                    })
            else:
                # 화자 분리 실패 시 기존 방식으로 폴백
                for segment in whisper_segments:
                    result_data["segments"].append({
                        "start": round(segment.start, 3),
                        "end": round(segment.end, 3),
                        "speaker": "SPEAKER_00", # 기본 화자
                        "text": segment.text.strip()
                    })

            print("[STT] 5. 모든 자막 처리 완료. 결과 파일 반환 중...", flush=True)
            # 임시 오디오 파일 삭제
            if os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass
                
            return json.dumps(result_data, ensure_ascii=False, indent=2)

        except Exception as e:
            import json, traceback
            return json.dumps({"error": f"STT 변환 중 문제가 발생했습니다: {str(e)}", "traceback": traceback.format_exc()}, ensure_ascii=False)
            
    def _format_time(self, seconds: float) -> str:
        """초(float)를 MM:SS.ms (예: 01:23.456) 형식으로 변환"""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{mins:02d}:{secs:02d}.{ms:03d}"