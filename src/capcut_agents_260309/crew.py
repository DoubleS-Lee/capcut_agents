from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from .tools.custom_tool import CapCutTool # 우리가 만든 캡컷 연동 도구
import os
from dotenv import load_dotenv

load_dotenv()

@CrewBase
class CapcutAgents260309():
    """감탄사 및 리액션 클립 추출 전용 시스템"""

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
    def emotion_scout(self) -> Agent:
        return Agent(
            config=self.agents_config['emotion_scout'], 
            llm=self.gemini, 
            verbose=True
        )

    @agent
    def capcut_engineer(self) -> Agent:
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
    def emotion_detection_task(self) -> Task:
        return Task(config=self.tasks_config['emotion_detection_task'])

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
            process=Process.sequential, 
            verbose=True,
        )
