import os
import sys

print('=== 환경 변수 PATH 중 NVIDIA/CUDA 관련 경로 ===')
paths = os.environ.get('PATH', '').split(os.pathsep)
for p in paths:
    if 'cuda' in p.lower() or 'nvidia' in p.lower():
        print(p)

print('\n=== ctranslate2 CUDA 테스트 ===')
try:
    import ctranslate2
    print('ctranslate2 버전:', ctranslate2.__version__)
    types = ctranslate2.get_supported_compute_types('cuda')
    print('CUDA 지원 여부:', types)
    print('CUDA 사용 가능!')
except Exception as e:
    print('오류 발생:', e)
