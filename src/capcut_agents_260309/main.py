#!/usr/bin/env python
import sys
import io
import warnings

# Windows 환경 등에서 이모지 출력 시 발생하는 UnicodeEncodeError 방지 (이모지 제거로 불필요)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from datetime import datetime

from capcut_agents_260309.crew import CapcutAgents260309

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    """
    Run the crew.
    """
    import argparse
    import os

    parser = argparse.ArgumentParser(description="AI 감탄사 소스 추출 시스템")
    parser.add_argument("--path", type=str, default="./raw_videos", help="원본 영상 폴더 경로")
    parser.add_argument("--cmd", type=str, default="영상 내의 모든 감탄사와 리액션 구간을 하나도 빠짐없이 소스로 추출해 줘. 시간 제한을 두지 마.", help="추가 지시사항")
    
    args, _ = parser.parse_known_args()

    # 경로를 절대 경로로 변환 및 슬래시(/)로 통일 (캡컷 호환성)
    abs_video_folder = os.path.abspath(args.path).replace('\\', '/')

    try:
        video_files = [f for f in os.listdir(abs_video_folder) if f.lower().endswith(('.mp4', '.mov'))]
        video_count = len(video_files)
        
        if video_count == 0:
            print(f"[에러] '{abs_video_folder}' 폴더 안에 영상 파일(mp4, mov)이 하나도 없습니다!")
            sys.exit(1)
            
        file_list_str = ", ".join(video_files)
        # 전체 절대 경로 리스트 생성 (슬래시 변환 적용)
        abs_file_paths = [os.path.join(abs_video_folder, f).replace('\\', '/') for f in video_files]
        abs_file_paths_str = ", ".join(abs_file_paths)
        
    except FileNotFoundError:
        print(f"[에러] '{abs_video_folder}' 폴더를 찾을 수 없습니다. 경로를 확인해 주세요.")
        sys.exit(1)

    print("[시작] AI 방송국: 감탄사 추출 시스템 가동을 시작합니다!")
    print(f"[타겟] 타겟 폴더: {abs_video_folder}")
    print(f"[지시] 총괄 지시: {args.cmd}\n")

    # [사전 작업]: 미리 추출된 STT 결과 파일(stt_result.json) 확인 및 추출
    stt_output_path = os.path.join(abs_video_folder, "stt_result.json")
    
    if not os.path.exists(stt_output_path):
        print(f"[안내] 대본 파일({stt_output_path})을 찾을 수 없어 자막 추출을 먼저 진행합니다.")
        try:
            from capcut_agents_260309.tools.stt_tool import STTTool
            main_video_path = os.path.join(abs_video_folder, sorted(video_files)[0])
            print(f"대상 영상: {main_video_path}")
            print("대본 추출 중... (시간이 소요될 수 있습니다)")
            
            tool = STTTool()
            result_text = tool._run(main_video_path)
            
            with open(stt_output_path, "w", encoding="utf-8") as f:
                f.write(result_text)
                
            print("[성공] 대본 추출 완료!\n")
        except Exception as e:
            print(f"[에러] STT 추출 중 문제가 발생했습니다: {e}")
            sys.exit(1)

    try:
        with open(stt_output_path, "r", encoding="utf-8") as f:
            stt_result_data = f.read()
        import json
        stt_json = json.loads(stt_result_data)
        
        # 화자 목록 및 샘플 대사 추출
        speaker_samples = {}
        for seg in stt_json.get('segments', []):
            spk = seg.get('speaker', 'UNKNOWN')
            text = seg.get('text', '').strip()
            if spk not in speaker_samples:
                speaker_samples[spk] = []
            if len(speaker_samples[spk]) < 3: # 화자당 최대 3개의 샘플 문장 수집
                speaker_samples[spk].append(text)
        
        speakers = sorted(speaker_samples.keys())
        print(f"[STT] 대본 로드 성공! 등장인물 분석 완료.")
        
        print("\n" + "="*50)
        print(" [화자별 대표 대사 샘플]")
        print("="*50)
        for i, spk in enumerate(speakers):
            samples = " | ".join(speaker_samples[spk])
            print(f"{i+1}. {spk:10} : {samples[:80]}...") # 길면 생략
        print(f"{len(speakers)+1}. 모든 화자 추출")
        print("="*50)
        
        choice = input(f"\n어떤 화자의 리액션을 추출할까요? 번호를 입력하세요 (1~{len(speakers)+1}): ").strip()
        selected_speaker = "ALL"
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(speakers):
                selected_speaker = speakers[idx]
            elif idx == len(speakers):
                selected_speaker = "ALL"
        
        print(f"\n[확인] '{selected_speaker}' 화자의 짧은 리액션만 골라내어 소스를 만듭니다.\n")
        
    except Exception as e:
        print(f"[에러] 대본 파일 분석 중 오류 발생: {e}")
        sys.exit(1)

    inputs = {
        'video_folder_path': abs_video_folder,
        'video_count': video_count,
        'video_files': file_list_str,
        'abs_video_paths': abs_file_paths_str,
        'user_prompt': args.cmd,
        'selected_speaker': selected_speaker, # 선택된 화자 추가
        'stt_data': stt_result_data.replace("{", "{{").replace("}", "}}")
    }

    try:
        CapcutAgents260309().crew().kickoff(inputs=inputs)
        print("\n[완료] 모든 편집 작업 완료!")
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


def run_programmatic(video_folder: str, cmd: str, selected_speaker: str,
                     output_dir: str = "", stt_data: str = "",
                     video_paths: list = None,
                     progress_cb=None):
    """
    GUI에서 직접 호출하는 함수. input() 없이 모든 파라미터를 인수로 받음.
    video_paths: GUI에서 선택한 특정 파일 경로 목록. 없으면 stt_data의 file 필드로 추론.
    progress_cb(message): 로그 메시지를 GUI로 전달하는 콜백.
    """
    import os, json

    def log(msg):
        print(msg, flush=True)
        if progress_cb:
            progress_cb(msg)

    if output_dir:
        os.environ["CAPCUT_OUTPUT_DIR"] = output_dir

    abs_video_folder = os.path.abspath(video_folder).replace("\\", "/")

    # stt_data가 없으면 파일에서 읽기
    if not stt_data:
        stt_path = os.path.join(abs_video_folder, "stt_result.json")
        if os.path.exists(stt_path):
            with open(stt_path, "r", encoding="utf-8") as f:
                stt_data = f.read()
        else:
            log("[에러] stt_result.json 파일을 찾을 수 없습니다. 먼저 STT를 실행하세요.")
            return

    # abs_video_paths: GUI 선택 파일 → stt_data의 file 필드 → 폴더 전체 순으로 결정
    if video_paths:
        abs_file_paths_str = ", ".join(
            os.path.abspath(p).replace("\\", "/") for p in video_paths
        )
    else:
        # STT JSON에서 파일명 추출하여 단일 경로만 전달 (에이전트 오인 방지)
        try:
            stt_obj = json.loads(stt_data)
            stt_file = stt_obj.get("file", "")
            if stt_file:
                abs_file_paths_str = os.path.join(abs_video_folder, stt_file).replace("\\", "/")
            else:
                raise ValueError("file 필드 없음")
        except Exception:
            # 폴더 전체 폴백
            video_files_all = [f for f in os.listdir(abs_video_folder)
                               if f.lower().endswith((".mp4", ".mov"))]
            abs_file_paths_str = ", ".join(
                os.path.join(abs_video_folder, f).replace("\\", "/") for f in video_files_all
            )

    log(f"[시작] 화자: {selected_speaker} | 지시: {cmd}")
    log(f"[정보] 영상 경로: {abs_file_paths_str}")

    inputs = {
        "video_folder_path": abs_video_folder,
        "abs_video_paths": abs_file_paths_str,
        "user_prompt": cmd,
        "selected_speaker": selected_speaker,
        "stt_data": stt_data.replace("{", "{{").replace("}", "}}"),
    }

    CapcutAgents260309().crew().kickoff(inputs=inputs)
    log("[완료] 캡컷 프로젝트 생성 완료!")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        CapcutAgents260309().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        CapcutAgents260309().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }

    try:
        CapcutAgents260309().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json

    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")

    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")

    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": "",
        "current_year": ""
    }

    try:
        result = CapcutAgents260309().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")
