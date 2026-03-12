import sys
print("Hello starting test")
from capcut_agents_260309.tools.stt_tool import STTTool
print("Imported STTTool")
tool = STTTool()
print("Initialized tool")
result = tool._run("raw_videos/20260303_150107.mp4")
print("Result:")
print(result)