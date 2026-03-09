# mcp_server.py
from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# 브라우저로 찔러봤을 때 "가게 문 열었어요!"라고 대답하는 부분
@app.route('/', methods=['GET'])
def home():
    return "✅ CapCut MCP Server is RUNNING on port 9000! 에이전트의 명령을 기다리는 중..."

# 6번 에이전트가 편집 지시서(JSON)를 들고 찾아올 창구
@app.route('/api/create_draft', methods=['POST'])
def create_draft():
    # 에이전트가 보낸 편집 데이터를 받습니다.
    data = request.json
    print("\n[서버 수신 완료] 6번 에이전트가 편집 지시서를 보냈습니다!")
    
    # ---------------------------------------------------------
    # 수신된 데이터를 바탕으로 실제 CapCut 호환 Draft 폴더 구조 생성
    # ---------------------------------------------------------
    output_dir = "output"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_folder_name = f"Draft_{timestamp}"
    draft_dir = os.path.join(output_dir, draft_folder_name)
    os.makedirs(draft_dir, exist_ok=True)
    
    # 1. AI 편집 지시서 원본 보존
    plan_file_path = os.path.join(draft_dir, "ai_edit_plan.json")
    with open(plan_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    # 2. CapCut draft_meta_info.json 생성
    meta_info = {
        "draft_materials": [],
        "draft_name": draft_folder_name,
        "draft_root_path": os.path.abspath(draft_dir),
        "id": timestamp,
        "tm_draft_create": int(datetime.now().timestamp() * 1000000),
        "tm_draft_modified": int(datetime.now().timestamp() * 1000000),
        "tm_duration": 0
    }
    with open(os.path.join(draft_dir, "draft_meta_info.json"), 'w', encoding='utf-8') as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=4)
        
    # 3. CapCut draft_content.json 생성 (타임라인/트랙 템플릿)
    content_info = {
        "materials": {
            "videos": [],
            "texts": [],
            "transitions": [],
            "speeds": [],
            "canvases": []
        },
        "tracks": [
            {
                "id": "track_video_main",
                "type": "video",
                "segments": []
            }
        ]
    }
    with open(os.path.join(draft_dir, "draft_content.json"), 'w', encoding='utf-8') as f:
        json.dump(content_info, f, ensure_ascii=False, indent=4)
        
    print(f"💾 캡컷용 Draft 프로젝트가 생성되었습니다: {draft_dir}")
    print(f"  👉 이 폴더를 CapCut PC의 Drafts 폴더로 복사하면 프로젝트가 열립니다.")
    
    # 에이전트에게 "작업 다 끝났어!"라고 알려줌
    return jsonify({
        "status": "success", 
        "message": f"캡컷 Draft 프로젝트가 성공적으로 생성되었습니다! 경로: {draft_dir}"
    }), 200

if __name__ == '__main__':
    print("🚀 CapCut MCP 서버를 가동합니다. (포트: 9000)")
    # 포트 9000번에서 24시간 대기 모드 시작
    app.run(host='0.0.0.0', port=9000)