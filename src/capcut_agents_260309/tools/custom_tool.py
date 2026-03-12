from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import requests # MCP 서버와 통신하기 위해 필요합니다

class CapCutToolInput(BaseModel):
    """캡컷 도구에 전달할 데이터의 형식입니다."""
    command: str = Field(..., description="캡컷에서 실행할 명령어 (예: 'create_draft')")
    details: str = Field(
        ..., 
        description="""
        명령어에 대한 상세 내용. 반드시 아래 JSON 형식을 텍스트로 변환하여 보내야 합니다.
        예시: {"videos": [{"path": "C:/video.mp4", "start_time": 0.0, "end_time": 5.5}], "texts": [{"content": "자막", "start_time": 1.0, "end_time": 3.0}]}
        """
    )

class CapCutTool(BaseTool):
    name: str = "CapCut_Editor"
    description: str = (
        "이 도구는 실제 캡컷(CapCut) 소프트웨어를 제어합니다. "
        "영상을 자르거나, 자막을 넣거나, 시각 효과를 넣을 때 반드시 이 도구를 사용해야 합니다."
    )
    args_schema: Type[BaseModel] = CapCutToolInput

    def _run(self, command: str, details: str) -> str:
        # 1. 실제 캡컷 MCP 서버의 주소 (서버가 실행 중이어야 합니다)
        mcp_url = "http://localhost:9000/api/create_draft" 
        
        # 2. 에이전트(Gemini)가 결정한 명령을 서버로 전송
        payload = {
            "action": command,
            "params": {"description": details}
        }

        try:
            # 실제로 MCP 서버에 '일 시키기'
            response = requests.post(mcp_url, json=payload, timeout=10)
            if response.status_code == 200:
                return f"캡컷 작업 성공: {command} ({details}) 완료."
            else:
                return f"캡컷 연결은 됐으나 오류 발생: {response.text}"
        except Exception as e:
            # 서버가 안 켜져 있으면 여기가 실행됩니다
            return f"오류: 캡컷 MCP 서버가 응답하지 않습니다. (주소: {mcp_url}). 서버가 켜져 있는지 확인하세요."