from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from .tools.custom_tool import CapCutTool # 우리가 만든 캡컷 연동 도구
from .tools.stt_tool import STTTool # 새로 만든 STT 도구 추가
from .tools.vision_tool import VisionTool # 새로 만든 Vision 도구 추가
import os
from dotenv import load_dotenv

load_dotenv()

@CrewBase
class CapcutAgents260309():
    """CapCut Video Editing Automation Crew"""

    def __init__(self):
        # 최신 CrewAI 방식의 LLM 설정
        self.gemini = LLM(
            model="gemini/gemini-3.1-flash-lite-preview",
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )

    # ==========================================
    # 1. 에이전트 정의 (agents.yaml 기반)
    # ==========================================

    @agent
    def sync_engineer(self) -> Agent:
        return Agent(config=self.agents_config['sync_engineer'], llm=self.gemini, verbose=True)

    @agent
    def script_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['script_analyst'], 
            llm=self.gemini, 
            tools=[STTTool()], # 스크립트 분석가에게 STT 귀를 달아줍니다!
            verbose=True
        )

    @agent
    def story_director(self) -> Agent:
        return Agent(config=self.agents_config['story_director'], llm=self.gemini, verbose=True)

    @agent
    def visual_director(self) -> Agent:
        return Agent(
            config=self.agents_config['visual_director'], 
            llm=self.gemini, 
            tools=[VisionTool()], # 비주얼 디렉터에게 시각 분석 도구(눈)를 장착!
            verbose=True
        )

    @agent
    def main_pd(self) -> Agent:
        return Agent(config=self.agents_config['main_pd'], llm=self.gemini, verbose=True)

    @agent
    def motion_designer(self) -> Agent:
        return Agent(config=self.agents_config['motion_designer'], llm=self.gemini, verbose=True)

    @agent
    def capcut_engineer(self) -> Agent:
        # 🚨 중요: 캡컷 도구(손)는 이 천재 개발자 에이전트에게만 쥐여줍니다!
        return Agent(
            config=self.agents_config['capcut_engineer'],
            llm=self.gemini,
            tools=[CapCutTool()], 
            verbose=True
        )

    # ==========================================
    # 2. 태스크(작업) 정의 (tasks.yaml과 연결)
    # ==========================================
    
    @task
    def sync_task(self) -> Task:
        return Task(config=self.tasks_config['sync_task'])

    @task
    def analysis_task(self) -> Task:
        return Task(config=self.tasks_config['analysis_task'])

    @task
    def story_task(self) -> Task:
        return Task(config=self.tasks_config['story_task'])

    @task
    def visual_task(self) -> Task:
        return Task(config=self.tasks_config['visual_task'])

    @task
    def editing_task(self) -> Task:
        return Task(config=self.tasks_config['editing_task'])

    @task
    def motion_task(self) -> Task:
        return Task(config=self.tasks_config['motion_task'])

    @task
    def capcut_export_task(self) -> Task:
        return Task(config=self.tasks_config['capcut_export_task'])

    # ==========================================
    # 3. 크루 조립 및 실행 방식 설정
    # ==========================================

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential, # 위에서 아래로 순서대로 작업 진행
            verbose=True,
        )