# mcp_server.py
from flask import Flask, request, jsonify
import json
import os
import uuid
import shutil
from datetime import datetime
import traceback
import re
from moviepy import VideoFileClip

app = Flask(__name__)

# 레퍼런스 템플릿 경로 및 출력 경로 설정
TEMPLATE_DIR = r"D:\00.Google CLI\capcut_agents_260309\reference\com.lveditor.draft\0226"
OUTPUT_BASE_DIR = r"D:\00.Google CLI\capcut_agents_260309\output"

# 전역 변수로 영상 길이 캐시
video_metadata_cache = {}

def get_video_metadata(file_path):
    """영상의 실제 길이를 마이크로초(MU) 단위로 반환합니다."""
    if file_path in video_metadata_cache:
        return video_metadata_cache[file_path]
    try:
        with VideoFileClip(file_path) as clip:
            duration_mu = int(clip.duration * 1000000)
            video_metadata_cache[file_path] = duration_mu
            return duration_mu
    except Exception as e:
        print(f"⚠️ 영상 메타데이터 추출 실패 ({file_path}): {e}")
        return 3600 * 1000000

def copy_template_to_new_draft(draft_name):
    """레퍼런스 폴더를 통째로 복사하여 새로운 초안 폴더를 만듭니다."""
    new_draft_dir = os.path.join(OUTPUT_BASE_DIR, draft_name)
    if os.path.exists(new_draft_dir):
        shutil.rmtree(new_draft_dir)
    
    if not os.path.exists(TEMPLATE_DIR):
        print(f"❌ 템플릿 폴더가 없습니다: {TEMPLATE_DIR}")
        os.makedirs(new_draft_dir, exist_ok=True)
        return new_draft_dir
        
    shutil.copytree(TEMPLATE_DIR, new_draft_dir)
    return new_draft_dir

def extract_json(text):
    """문자열에서 JSON 부분만 추출하여 객체로 반환합니다."""
    if isinstance(text, dict): return text
    try:
        clean_text = re.sub(r'```json\s*|```', '', text).strip()
        return json.loads(clean_text)
    except:
        try:
            match = re.search(r'(\{.*\})', text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except:
            pass
    return None

@app.route('/', methods=['GET'])
def home():
    return "✅ CapCut MCP Server is RUNNING on port 9000!"

@app.route('/api/create_draft', methods=['POST'])
def create_draft():
    try:
        data = request.json
        print("\n[서버 수신] 편집 지시서를 파싱합니다...")
        
        description = data.get("params", {}).get("description", "")
        ai_plan = extract_json(description)
        
        if ai_plan is None:
            print("⚠️ JSON 추출 실패. 원본 데이터 사용 시도...")
            ai_plan = data
            
        if "videos" not in ai_plan: ai_plan["videos"] = []
        if "texts" not in ai_plan: ai_plan["texts"] = []

        # 2. 새로운 Draft 폴더 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_name = f"Reaction_Maker_{timestamp}"
        new_draft_dir = copy_template_to_new_draft(draft_name)
        
        # 3. draft_content.json 수정
        content_path = os.path.join(new_draft_dir, "draft_content.json")
        if not os.path.exists(content_path):
            content_info = {"materials": {"videos": [], "texts": []}, "tracks": []}
        else:
            with open(content_path, 'r', encoding='utf-8') as f:
                content_info = json.load(f)
            
        content_info["materials"]["videos"] = []
        content_info["materials"]["texts"] = []
        content_info["tracks"] = [
            {"id": str(uuid.uuid4()), "type": "video", "segments": []},
            {"id": str(uuid.uuid4()), "type": "text", "segments": []}
        ]
        
        MU_SEC = 1000000
        current_timeline_time = 0
        total_duration = 0
        path_to_mat_id = {}

        # A. 비디오 처리
        for video in ai_plan.get("videos", []):
            v_path = video.get("path", "").replace("\\", "/")
            if not v_path or not os.path.exists(v_path):
                print(f"⚠️ 파일 없음: {v_path}")
                continue
            
            if v_path not in path_to_mat_id:
                mat_id = str(uuid.uuid4())
                actual_duration = get_video_metadata(v_path)
                content_info["materials"]["videos"].append({
                    "id": mat_id, "path": v_path, "type": "video",
                    "duration": actual_duration, "material_name": os.path.basename(v_path), "has_audio": True
                })
                path_to_mat_id[v_path] = mat_id
            
            target_mat_id = path_to_mat_id[v_path]
            v_start = int(float(video.get("start_time", 0)) * MU_SEC)
            v_end = int(float(video.get("end_time", 5)) * MU_SEC)
            v_duration = v_end - v_start
            
            if v_duration <= 0: continue
            
            content_info["tracks"][0]["segments"].append({
                "id": str(uuid.uuid4()), "material_id": target_mat_id,
                "source_timerange": {"duration": v_duration, "start": v_start},
                "target_timerange": {"duration": v_duration, "start": current_timeline_time},
                "speed": 1.0, "visible": True,
                "clip": {"alpha": 1.0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0.0, "y": 0.0}}
            })
            current_timeline_time += v_duration
            total_duration = max(total_duration, current_timeline_time)

        # B. 자막 처리
        for text_item in ai_plan.get("texts", []):
            t_content = text_item.get("content", "")
            if not t_content: continue
            
            t_start = int(float(text_item.get("start_time", 0)) * MU_SEC)
            t_end = int(float(text_item.get("end_time", 2)) * MU_SEC)
            t_duration = t_end - t_start
            if t_duration <= 0: continue
            
            mat_id = str(uuid.uuid4())
            content_json_str = json.dumps({
                "text": t_content,
                "styles": [{"range": [0, len(t_content)], "font": {"path": "C:/Windows/Fonts/malgun.ttf", "id": ""}}]
            }, ensure_ascii=False)
            
            content_info["materials"]["texts"].append({
                "id": mat_id, "type": "text", "content": content_json_str, "text_alpha": 1.0, "layer": 2
            })
            
            content_info["tracks"][1]["segments"].append({
                "id": str(uuid.uuid4()), "material_id": mat_id,
                "source_timerange": {"duration": t_duration, "start": 0},
                "target_timerange": {"duration": t_duration, "start": t_start},
                "visible": True,
                "clip": {"alpha": 1.0, "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": 0.0, "y": 0.0}}
            })
            total_duration = max(total_duration, t_end)

        content_info["duration"] = total_duration
        with open(content_path, 'w', encoding='utf-8') as f:
            json.dump(content_info, f, ensure_ascii=False, indent=4)
            
        meta_path = os.path.join(new_draft_dir, "draft_meta_info.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta_info = json.load(f)
            meta_info["draft_name"] = draft_name
            meta_info["draft_id"] = str(uuid.uuid4())
            meta_info["draft_fold_path"] = new_draft_dir.replace("\\", "/")
            meta_info["tm_duration"] = total_duration
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_info, f, ensure_ascii=False, indent=4)

        print(f"💾 [성공] 캡컷 프로젝트 생성 완료: {new_draft_dir}")
        return jsonify({"status": "success", "draft_path": new_draft_dir}), 200

    except Exception as e:
        print(f"❌ 서버 에러 발생!")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    print("🚀 CapCut MCP 서버를 가동합니다. (포트: 9000)")
    app.run(host='0.0.0.0', port=9000)
