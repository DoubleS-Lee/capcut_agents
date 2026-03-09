#!/usr/bin/env python
import sys
import io
import warnings

# Windows 환경 등에서 이모지 출력 시 발생하는 UnicodeEncodeError 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

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
            print(f"❌ 에러: '{args.path}' 폴더 안에 영상 파일(mp4, mov)이 하나도 없습니다!")
            sys.exit(1)
            
        file_list_str = ", ".join(video_files)
        
    except FileNotFoundError:
        print(f"❌ 에러: '{args.path}' 폴더를 찾을 수 없습니다. 경로를 확인해 주세요.")
        sys.exit(1)

    print("🎬 AI 방송국: 멀티캠 자동 편집 시스템 가동을 시작합니다!")
    print(f"📂 타겟 폴더: {args.path}")
    print(f"📢 총괄 지시: {args.cmd}\n")

    inputs = {
        'video_folder_path': args.path,
        'video_count': video_count,
        'video_files': file_list_str,
        'user_prompt': args.cmd
    }

    try:
        CapcutAgents260309().crew().kickoff(inputs=inputs)
        print("\n✅ 모든 편집 작업 완료!")
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
