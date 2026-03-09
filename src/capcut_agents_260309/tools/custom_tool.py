from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import requests # MCP 서버와 통신하기 위해 필요합니다

class CapCutToolInput(BaseModel):
    """캡컷 도구에 전달할 데이터의 형식입니다."""
    command: str = Field(..., description="캡컷에서 실행할 구체적인 편집 명령어 (예: '자막 추가', '컷 편집', '줌 인')")
    details: str = Field(..., description="명령어에 대한 상세 내용 (예: '자막 내용을 안녕하세요로 설정', '30초 지점 컷')")

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