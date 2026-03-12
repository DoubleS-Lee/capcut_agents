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

    parser = argparse.ArgumentParser(description="AI 멀티캠 편집 시스템")
    parser.add_argument("--path", type=str, default="./raw_videos", help="원본 영상 폴더 경로")
    parser.add_argument("--cmd", type=str, default="가장 재미있고 역동적으로 편집해 줘.", help="메인 PD에게 내릴 추가 지시사항")
    
    args, _ = parser.parse_known_args()

    try:
        video_files = [f for f in os.listdir(args.path) if f.lower().endswith(('.mp4', '.mov'))]
        video_count = len(video_files)
        
        if video_count == 0:
            print(f"[에러] '{args.path}' 폴더 안에 영상 파일(mp4, mov)이 하나도 없습니다!")
            sys.exit(1)
            
        file_list_str = ", ".join(video_files)
        
    except FileNotFoundError:
        print(f"[에러] '{args.path}' 폴더를 찾을 수 없습니다. 경로를 확인해 주세요.")
        sys.exit(1)

    print("[시작] AI 방송국: 멀티캠 자동 편집 시스템 가동을 시작합니다!")
    print(f"[타겟] 타겟 폴더: {args.path}")
    print(f"[지시] 총괄 지시: {args.cmd}\n")

    # [사전 작업]: 미리 추출된 STT 결과 파일(stt_result.json) 확인 및 추출
    stt_output_path = os.path.join(args.path, "stt_result.json")
    
    if not os.path.exists(stt_output_path):
        print(f"[안내] 대본 파일({stt_output_path})을 찾을 수 없어 자막 추출을 먼저 진행합니다.")
        try:
            from capcut_agents_260309.tools.stt_tool import STTTool
            main_video_path = os.path.join(args.path, sorted(video_files)[0])
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
        print(f"[STT] 대본 파일(JSON) 로드 성공! (경로: {stt_output_path})\n")
    except Exception as e:
        print(f"[에러] 대본 파일 로드 중 오류 발생: {e}")
        sys.exit(1)

    inputs = {
        'video_folder_path': args.path,
        'video_count': video_count,
        'video_files': file_list_str,
        'user_prompt': args.cmd,
        'stt_data': stt_result_data.replace("{", "{{").replace("}", "}}") # JSON 중괄호 이스케이프 처리
    }

    try:
        CapcutAgents260309().crew().kickoff(inputs=inputs)
        print("\n[완료] 모든 편집 작업 완료!")
    except Exception as e:
        raise Exception(f"An error occurred while running the crew: {e}")


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
