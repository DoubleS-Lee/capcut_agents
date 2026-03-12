import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from capcut_agents_260309.crew import CapcutAgents260309
from crewai import Crew, Process

def test_sync():
    print("🎬 오디오 동기화 에이전트(sync_engineer) 단독 테스트 시작...")
    
    # 크루 설정 불러오기
    crew_instance = CapcutAgents260309()
    
    # 타겟 폴더와 영상 파일 가져오기
    target_folder = os.path.abspath("./raw_videos")
    video_files = [f for f in os.listdir(target_folder) if f.lower().endswith(('.mp4', '.mov'))]
    video_count = len(video_files)
    file_list_str = ", ".join(video_files)
    
    if video_count < 2:
        print(f"❌ 동기화 에이전트 테스트를 위해서는 최소 2개 이상의 영상이 필요합니다. 현재 {video_count}개 발견됨.")
        return
    
    print(f"📂 분석 대상 영상 ({video_count}개): {file_list_str}")
    
    # 동기화 에이전트와 태스크만 추출
    sync_agent = crew_instance.sync_engineer()
    sync_task_instance = crew_instance.sync_task()
    
    # 단독 크루 생성
    test_crew = Crew(
        agents=[sync_agent],
        tasks=[sync_task_instance],
        process=Process.sequential,
        verbose=True
    )
    
    inputs = {
        'video_folder_path': target_folder,
        'video_count': video_count,
        'video_files': file_list_str,
        'user_prompt': "테스트용 실행입니다."
    }
    
    # 실행
    result = test_crew.kickoff(inputs=inputs)
    
    # 결과를 파일로 저장
    output_path = "sync_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        # result.raw는 실제 문자열 결과물을 반환
        f.write(str(result.raw))
        
    print(f"\\n✅ 동기화 결과가 {output_path} 파일로 저장되었습니다.")

if __name__ == "__main__":
    test_sync()
