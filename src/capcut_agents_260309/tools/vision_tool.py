from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import os
import cv2
import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

class VisionToolInput(BaseModel):
    """비전 분석 도구에 전달할 데이터의 형식입니다."""
    video_path: str = Field(..., description="화면 구도를 분석할 원본 영상(.mp4, .mov 등)의 절대 또는 상대 경로입니다.")

class VisionTool(BaseTool):
    name: str = "Video_Vision_Tool"
    description: str = (
        "비디오 파일 경로를 받아 영상의 도입, 중반, 결말의 주요 프레임을 추출하고 "
        "AI(Gemini Vision)를 통해 화면 구도(풀샷, 바스트샷 등), 초점 나감 등의 NG 컷 판별, "
        "크롭(Crop) 가이드를 분석하여 리포트로 반환합니다."
    )
    args_schema: Type[BaseModel] = VisionToolInput

    def _run(self, video_path: str) -> str:
        if not os.path.exists(video_path):
            return f"오류: 파일을 찾을 수 없습니다: {video_path}"

        try:
            # 1. OpenCV로 비디오 파일 열기
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return f"오류: 비디오 파일을 열 수 없습니다. ({video_path})"

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # 2. 영상의 3개 지점(10%, 50%, 90%)에서 대표 프레임 추출
            target_frames = [int(total_frames * 0.1), int(total_frames * 0.5), int(total_frames * 0.9)]
            encoded_images = []

            for frame_idx in target_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    # 이미지를 JPEG로 압축 후 Base64 문자열로 인코딩 (LLM에게 전송하기 위함)
                    _, buffer = cv2.imencode('.jpg', frame)
                    img_str = base64.b64encode(buffer).decode('utf-8')
                    encoded_images.append(img_str)

            cap.release()

            if not encoded_images:
                return "오류: 비디오에서 프레임을 추출하지 못했습니다."

            # 3. Gemini 1.5 Pro (멀티모달 Vision 기능) 연결 설정
            # 시스템 환경변수(GEMINI_API_KEY 또는 GOOGLE_API_KEY)를 자동으로 사용합니다.
            llm = ChatGoogleGenerativeAI(
                model="gemini-3.1-flash-lite-preview",
                google_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            )

            # 4. 프롬프트와 이미지 데이터를 묶어서 전송
            prompt_text = (
                "당신은 영상 편집을 위한 수석 카메라 및 비주얼 감독입니다. "
                "첨부된 3장의 이미지는 하나의 영상에서 시간순(초반, 중반, 후반)으로 추출된 프레임들입니다. "
                "다음 세 가지를 분석하여 리포트를 작성해 주세요:\n"
                "1. 샷 종류 분류: 전체적인 구도가 풀샷(Full Shot), 바스트샷(Bust Shot), 클로즈업(Close-up) 중 어디에 해당하는지 분석하세요.\n"
                "2. NG 컷 판별: 화면이 심하게 흔들리거나, 피사체의 초점이 나갔거나, 피사체가 프레임 밖으로 벗어난 NG 구간으로 보이는 부분이 있는지 판별하세요.\n"
                "3. 크롭(Crop) 가이드: 만약 숏폼(9:16 비율)으로 크롭한다면, 주요 피사체(인물 등)를 중심으로 어느 부분을 잘라내야 할지 대략적인 가이드(예: 중앙 중심, 왼쪽 치우침 등)를 제시해 주세요."
            )
            
            content = [{"type": "text", "text": prompt_text}]
            for img_base64 in encoded_images:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                })

            message = HumanMessage(content=content)
            
            # AI에게 분석 요청!
            response = llm.invoke([message])

            return f"[{os.path.basename(video_path)} 비전 분석 결과]\n{response.content}"

        except Exception as e:
            return f"비전 분석 중 알 수 없는 오류 발생: {str(e)}"