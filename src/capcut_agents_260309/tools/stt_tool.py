from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import os
import speech_recognition as sr
from moviepy import VideoFileClip
import tempfile

class STTToolInput(BaseModel):
    """STT 도구에 전달할 데이터의 형식입니다."""
    video_path: str = Field(..., description="텍스트로 변환할 원본 영상(.mp4, .mov 등)의 절대 또는 상대 경로입니다.")

class STTTool(BaseTool):
    name: str = "Video_STT_Tool"
    description: str = (
        "이 도구는 영상 파일에서 오디오를 추출하고, 해당 오디오의 음성을 텍스트(대본)로 변환해 줍니다. "
        "영상의 내용을 파악하거나 스크립트를 분석할 때 반드시 이 도구에 영상 경로를 넣어 실행하세요."
    )
    args_schema: Type[BaseModel] = STTToolInput

    def _run(self, video_path: str) -> str:
        if not os.path.exists(video_path):
            return f"오류: 파일이 존재하지 않습니다. 경로를 확인하세요: {video_path}"

        try:
            # 1. 임시 폴더에 오디오 파일(.wav) 추출
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, "temp_extracted_audio.wav")
            
            # moviepy를 이용해 비디오에서 오디오만 뽑아내어 저장
            with VideoFileClip(video_path) as video:
                audio = video.audio
                if audio is None:
                    return f"결과: 영상에 오디오 트랙이 존재하지 않습니다. ({video_path})"
                # 로그 출력을 줄이기 위해 logger=None 설정
                audio.write_audiofile(audio_path, codec='pcm_s16le', logger=None)

            # 2. 추출된 오디오 파일을 SpeechRecognition으로 텍스트 변환
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                # 오디오 데이터 읽기
                audio_data = recognizer.record(source)
                
            # 구글의 무료 Web Speech API 사용 (한국어 설정)
            # 주의: 파일이 너무 길면 잘리거나 에러가 날 수 있습니다.
            text = recognizer.recognize_google(audio_data, language='ko-KR')
            
            # 임시 오디오 파일 삭제
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
            return f"[{os.path.basename(video_path)} STT 변환 결과]\n{text}"

        except sr.UnknownValueError:
            return "결과: 음성을 인식할 수 없습니다. (말소리가 없거나 노이즈가 심함)"
        except sr.RequestError as e:
            return f"오류: 구글 음성 인식 서비스에 접근할 수 없습니다. ({e})"
        except Exception as e:
            return f"오류: STT 변환 중 문제가 발생했습니다: {str(e)}"