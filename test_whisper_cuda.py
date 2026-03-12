import os
import sys
import faulthandler
import site
import numpy as np

# 강제 종료 시 로그 출력
faulthandler.enable()

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

for sp in site.getsitepackages():
    for nvidia_pkg in ['cublas', 'cudnn']:
        bin_path = os.path.join(sp, 'nvidia', nvidia_pkg, 'bin')
        if os.path.exists(bin_path):
            os.environ['PATH'] = bin_path + os.pathsep + os.environ['PATH']

from faster_whisper import WhisperModel

print("1. 모델 로딩 시작...")
model = WhisperModel("base", device="cuda", compute_type="float16")
print("2. 로딩 완료, 가짜 오디오 데이터 생성...")

# 1초짜리 가짜 오디오 데이터 (16000Hz) 생성
dummy_audio = np.zeros(16000, dtype=np.float32)

print("3. STT 변환(인퍼런스) 시작! 여기서 튕기면 cuDNN 연산 라이브러리 충돌입니다.")
try:
    segments, info = model.transcribe(dummy_audio, beam_size=5, language="ko")
    for segment in segments:
        pass
    print("4. 변환 완료 성공!")
except Exception as e:
    print("변환 중 에러 발생:", e)
