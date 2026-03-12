print("Start test script")
import sys
try:
    print("Importing STTTool")
    from capcut_agents_260309.tools.stt_tool import STTTool
    print("STTTool imported")
    
    print("Testing STT Tool...")
    tool = STTTool()
    video_path = "d:/00.Google CLI/capcut_agents_260309/raw_videos/20260303_150107.mp4"
    result = tool._run(video_path)
    print("=== Result ===")
    print(result)
except Exception as e:
    print("Exception occurred:", e)
print("End of test script")
