# mcp_server.py
from flask import Flask, request, jsonify
import json
import os
import uuid
import shutil
from datetime import datetime

app = Flask(__name__)

# 레퍼런스 템플릿 경로 (사용자님이 제공해주신 완벽한 캡컷 프로젝트 구조)
TEMPLATE_DIR = r"D:\00.Google CLI\capcut_agents_260309\reference\com.lveditor.draft\0226"
OUTPUT_BASE_DIR = r"D:\00.Google CLI\capcut_agents_260309\output"

@app.route('/', methods=['GET'])
def home():
    return "✅ CapCut MCP Server is RUNNING on port 9000! 에이전트의 명령을 기다리는 중..."

def copy_template_to_new_draft(draft_name):
    """레퍼런스 폴더를 통째로 복사하여 새로운 초안 폴더를 만듭니다."""
    new_draft_dir = os.path.join(OUTPUT_BASE_DIR, draft_name)
    if os.path.exists(new_draft_dir):
        shutil.rmtree(new_draft_dir) # 이미 있다면 삭제
    shutil.copytree(TEMPLATE_DIR, new_draft_dir)
    return new_draft_dir

@app.route('/api/create_draft', methods=['POST'])
def create_draft():
    data = request.json
    print("\n[서버 수신 완료] 에이전트가 편집 지시서를 보냈습니다!")
    
    # 1. 에이전트 데이터 파싱
    if "params" in data and "description" in data["params"]:
        try:
            ai_plan = json.loads(data["params"]["description"])
        except json.JSONDecodeError:
            print("⚠️ JSON 파싱 실패. 빈 데이터로 초기화합니다.")
            ai_plan = {"videos": [], "texts": []}
    else:
        ai_plan = data
        
    if "videos" not in ai_plan: ai_plan["videos"] = []
    if "texts" not in ai_plan: ai_plan["texts"] = []

    # 2. 새로운 Draft 폴더 생성 (템플릿 복사)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_name = f"AI_Draft_{timestamp}"
    new_draft_dir = copy_template_to_new_draft(draft_name)
    
    # 에이전트 원본 파일 저장
    with open(os.path.join(new_draft_dir, "ai_edit_plan.json"), 'w', encoding='utf-8') as f:
        json.dump(ai_plan, f, ensure_ascii=False, indent=4)

    # 3. draft_content.json 수정 (뼈대 유지 + 데이터 덮어쓰기)
    content_path = os.path.join(new_draft_dir, "draft_content.json")
    with open(content_path, 'r', encoding='utf-8') as f:
        content_info = json.load(f)
        
    # 기존 영상/자막 데이터 비우기 (템플릿에 남아있을지 모르는 기존 편집 찌꺼기 제거)
    content_info["materials"]["videos"] = []
    content_info["materials"]["texts"] = []
    content_info["tracks"] = [
        {"id": str(uuid.uuid4()), "type": "video", "segments": []}, # 영상 트랙
        {"id": str(uuid.uuid4()), "type": "text", "segments": []}   # 자막 트랙
    ]
    
    # --- 에이전트 데이터 -> CapCut 포맷 주입 ---
    MU_SEC = 1000000
    current_timeline_time = 0
    total_duration = 0
    
    # A. 비디오 처리
    for video in ai_plan.get("videos", []):
        try:
            v_path = video.get("path", "")
            if not os.path.isabs(v_path):
                # 상대 경로일 경우 raw_videos 기준 절대 경로로 변환
                v_path = os.path.abspath(os.path.join(os.path.dirname(OUTPUT_BASE_DIR), "raw_videos", v_path))
            v_path = v_path.replace("\\", "/") # 캡컷은 슬래시를 좋아합니다.
            if not v_path: continue
            
            v_start = int(float(video.get("start_time", 0)) * MU_SEC)
            v_end = int(float(video.get("end_time", 5)) * MU_SEC)
            v_duration = v_end - v_start
            if v_duration <= 0: continue
            
            mat_id = str(uuid.uuid4())
            seg_id = str(uuid.uuid4())
            
            # duration을 충분히 길게 설정 (CapCut이 source_timerange start를 0으로 리셋하지 않도록)
            material_duration = max(86400 * MU_SEC, v_end * 2)
            
            content_info["materials"]["videos"].append({
                "id": mat_id,
                "path": v_path,
                "type": "video",
                "duration": material_duration,
                "extra_type_option": 0,
                "has_audio": True,
                "material_name": os.path.basename(v_path)
            })
            
            content_info["tracks"][0]["segments"].append({
                "id": seg_id,
                "material_id": mat_id,
                "source_timerange": {"duration": v_duration, "start": v_start},
                "target_timerange": {"duration": v_duration, "start": current_timeline_time},
                "speed": 1.0,
                "volume": 1.0,
                "visible": True,
                "clip": {"alpha": 1.0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0.0, "y": 0.0}}
            })
            
            current_timeline_time += v_duration
            total_duration = max(total_duration, current_timeline_time)
        except Exception as e:
            print(f"비디오 파싱 오류: {e}")

    # B. 자막 처리
    for text_item in ai_plan.get("texts", []):
        try:
            t_content = text_item.get("content", "")
            if not t_content: continue
            
            t_start = int(float(text_item.get("start_time", 0)) * MU_SEC)
            t_end = int(float(text_item.get("end_time", 2)) * MU_SEC)
            t_duration = t_end - t_start
            if t_duration <= 0: continue
            
            mat_id = str(uuid.uuid4())
            seg_id = str(uuid.uuid4())
            
            content_json_str = json.dumps({
                "text": t_content,
                "styles": [{
                    "fill": {"content": {"render_type": "solid", "solid": {"color": [1, 1, 1]}}},
                    "font": {"path": "C:/Windows/Fonts/malgun.ttf", "id": ""},
                    "size": 15,
                    "range": [0, len(t_content)]
                }]
            }, ensure_ascii=False)
            
            content_info["materials"]["texts"].append({
                "id": mat_id,
                "type": "text",
                "content": content_json_str,
                "text_alpha": 1.0,
                "font_size": 15.0,
                "text_color": "#FFFFFF",
                "layer": 2
            })
            
            content_info["tracks"][1]["segments"].append({
                "id": seg_id,
                "material_id": mat_id,
                "source_timerange": {"duration": t_duration, "start": 0},
                "target_timerange": {"duration": t_duration, "start": t_start},
                "visible": True,
                "clip": {"alpha": 1.0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0.0, "y": 0.0}}
            })
            
            total_duration = max(total_duration, t_end)
        except Exception as e:
            print(f"자막 파싱 오류: {e}")

    content_info["duration"] = total_duration

    with open(content_path, 'w', encoding='utf-8') as f:
        json.dump(content_info, f, ensure_ascii=False, indent=4)
        
    # 4. draft_meta_info.json 갱신 (경로 및 이름 동기화)
    meta_path = os.path.join(new_draft_dir, "draft_meta_info.json")
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta_info = json.load(f)
        
    # 필수 메타데이터 덮어쓰기
    new_uuid = str(uuid.uuid4())
    meta_info["draft_name"] = draft_name
    meta_info["draft_id"] = new_uuid
    meta_info["draft_fold_path"] = new_draft_dir.replace("\\", "/") # 캡컷은 슬래시를 씁니다
    meta_info["tm_duration"] = total_duration
    meta_info["tm_draft_modified"] = int(datetime.now().timestamp() * 1000000)
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=4)

    print(f"\n💾 [성공] 캡컷 완벽 호환 Draft 프로젝트 생성 완료!")
    print(f"  👉 생성 경로: {new_draft_dir}")
    print(f"  👉 [필수] 이 폴더를 복사하여 캡컷 프로젝트 경로(com.lveditor.draft) 안에 붙여넣으세요.\n")
    
    return jsonify({
        "status": "success", 
        "message": f"캡컷 Draft 프로젝트 생성 완료: {new_draft_dir}"
    }), 200

if __name__ == '__main__':
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    print("🚀 CapCut MCP 서버를 가동합니다. (포트: 9000)")
    app.run(host='0.0.0.0', port=9000)
