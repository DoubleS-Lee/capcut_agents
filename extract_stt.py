import os
import sys
import faulthandler

# C++ 강제 종료 시 콜스택 및 버퍼 없는 즉각 출력
faulthandler.enable()
sys.stdout.reconfigure(line_buffering=True)

# OpenMP 중복 로드 시 강제 종료되는 버그 방지
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# NVIDIA cuBLAS 및 cuDNN 라이브러리를 PATH에 강제 추가 (ctranslate2 런타임 충돌 방지)
import site
for sp in site.getsitepackages():
    for nvidia_pkg in ['cublas', 'cudnn']:
        bin_path = os.path.join(sp, 'nvidia', nvidia_pkg, 'bin')
        if os.path.exists(bin_path):
            os.environ['PATH'] = bin_path + os.pathsep + os.environ['PATH']

import argparse

# Windows 환경 등에서 이모지 출력 시 발생하는 UnicodeEncodeError 방지
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, "src"))

try:
    from capcut_agents_260309.tools.stt_tool import STTTool
except ImportError as e:
    print(f"[오류] 모듈을 불러올 수 없습니다. 경로를 확인해주세요: {e}")
    sys.exit(1)

def extract_stt(video_folder):
    print("[STT 사전 작업] 시작...")
    
    # 폴더 내의 영상 파일 찾기
    video_files = [f for f in os.listdir(video_folder) if f.lower().endswith(('.mp4', '.mov'))]
    
    if not video_files:
        print(f"[오류] '{video_folder}' 폴더 안에 영상 파일이 없습니다.")
        return

    # 첫 번째 영상을 메인 영상으로 가정
    main_video_name = sorted(video_files)[0]
    main_video_path = os.path.join(video_folder, main_video_name)
    
    print(f"대상 영상: {main_video_path}")
    print("대본을 추출하고 있습니다. (GPU 가속 사용 시 빠릅니다)...")
    
    try:
        tool = STTTool()
        result_text = tool._run(main_video_path)
        
        output_path = os.path.join(video_folder, "stt_result.json")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result_text)
            
        print(f"[성공] 대본 추출 완료! 결과가 다음 경로에 저장되었습니다:")
        print(f"   -> {output_path}")
        
    except Exception as e:
        print(f"[오류] STT 추출 중 문제가 발생했습니다: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="에이전트 실행 전 STT 대본 추출기")
    parser.add_argument("--path", type=str, default="./raw_videos", help="원본 영상이 있는 폴더 경로")
    args = parser.parse_args()
    
    extract_stt(args.path)
