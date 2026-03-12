from capcut_agents_260309.crew import CapcutAgents260309
from crewai import Task
import os

def test_agent():
    print("Initializing Crew...")
    project = CapcutAgents260309()
    
    print("Getting script analyst...")
    analyst = project.script_analyst()
    
    print("Creating task...")
    task = project.analysis_task()
    task.agent = analyst
    task.description = task.description.format(
        video_folder_path="raw_videos",
        video_files="20260303_150107.mp4"
    )
    
    print("Executing task...")
    result = task.execute_sync()
    print("=== Task Result ===")
    print(result)

if __name__ == "__main__":
    test_agent()
