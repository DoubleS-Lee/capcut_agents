# mcp_server.py
from flask import Flask, request, jsonify
import json
import os
import uuid
import copy
import shutil
from datetime import datetime
import traceback
import re
from moviepy import VideoFileClip

app = Flask(__name__)

# [설정] 경로 고정
BASE_DIR = r"D:\00.Google CLI\capcut_agents_260309"
TEMPLATE_DIR = os.path.join(BASE_DIR, "reference", "com.lveditor.draft", "0226")
OUTPUT_BASE_DIR = os.path.join(BASE_DIR, "output")

video_metadata_cache = {}

def get_video_metadata(file_path):
    """영상의 (duration_microseconds, width, height) 반환"""
    if file_path in video_metadata_cache:
        return video_metadata_cache[file_path]
    try:
        with VideoFileClip(file_path) as clip:
            dur = int(clip.duration * 1_000_000)
            w, h = int(clip.w), int(clip.h)
            video_metadata_cache[file_path] = (dur, w, h)
            return dur, w, h
    except:
        return 3600 * 1_000_000, 1920, 1080

def extract_json(text):
    if isinstance(text, dict): return text
    try:
        s = str(text)
        clean = re.sub(r'```json\s*|```', '', s).strip()
        return json.loads(clean)
    except:
        try:
            match = re.search(r'(\{.*\})', str(text), re.DOTALL)
            if match: return json.loads(match.group(1))
        except: pass
    return None

def make_video_material(vid_id, path, duration_mu, width, height):
    return {
        "aigc_history_id": "", "aigc_item_id": "", "aigc_type": "none",
        "audio_fade": None,
        "beauty_body_auto_preset": None, "beauty_body_preset_id": "",
        "beauty_face_auto_preset": {"name": "", "preset_id": "", "rate_map": "", "scene": ""},
        "beauty_face_auto_preset_infos": [], "beauty_face_preset_infos": [],
        "cartoon_path": "", "category_id": "", "category_name": "",
        "check_flag": 62978047, "content_feature_info": None, "corner_pin": None,
        "crop": {"lower_left_x": 0.0, "lower_left_y": 1.0, "lower_right_x": 1.0,
                 "lower_right_y": 1.0, "upper_left_x": 0.0, "upper_left_y": 0.0,
                 "upper_right_x": 1.0, "upper_right_y": 0.0},
        "crop_ratio": "free", "crop_scale": 1.0,
        "duration": duration_mu, "extra_type_option": 0,
        "formula_id": "", "freeze": None,
        "has_audio": True, "has_sound_separated": False,
        "height": height, "id": vid_id,
        "intensifies_audio_path": "", "intensifies_path": "",
        "is_ai_generate_content": False, "is_copyright": False,
        "is_text_edit_overdub": False, "is_unified_beauty_mode": False,
        "live_photo_cover_path": "", "live_photo_timestamp": -1,
        "local_id": "", "local_material_from": "", "local_material_id": "",
        "material_id": "", "material_name": os.path.basename(path),
        "material_url": "",
        "matting": {
            "custom_matting_id": "", "enable_matting_stroke": False,
            "expansion": 0, "feather": 0, "flag": 0,
            "has_use_quick_brush": False, "has_use_quick_eraser": False,
            "interactiveTime": [], "path": "", "reverse": False, "strokes": []
        },
        "media_path": "", "multi_camera_info": None, "object_locked": None,
        "origin_material_id": "", "path": path,
        "picture_from": "none", "picture_set_category_id": "", "picture_set_category_name": "",
        "request_id": "", "reverse_intensifies_path": "", "reverse_path": "",
        "smart_match_info": None, "smart_motion": None,
        "source": 0, "source_platform": 0,
        "stable": {"matrix_path": "", "stable_level": 0,
                   "time_range": {"duration": 0, "start": 0}},
        "surface_trackings": [], "team_id": "", "type": "video",
        "video_algorithm": {
            "ai_background_configs": [], "ai_expression_driven": None,
            "ai_in_painting_config": [], "ai_motion_driven": None,
            "aigc_generate": None, "aigc_generate_list": [], "algorithms": [],
            "complement_frame_config": None, "deflicker": None,
            "gameplay_configs": [], "image_interpretation": None,
            "motion_blur_config": None, "mouth_shape_driver": None,
            "noise_reduction": None, "path": "", "quality_enhance": None,
            "skip_algorithm_index": []
        },
        "video_mask_shadow": None, "video_mask_stroke": None,
        "width": width
    }

def make_video_segment(seg_id, mat_id, source_start, duration_mu, target_start, render_index=0):
    return {
        "caption_info": None, "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.0}
        },
        "color_correct_alg_result": "", "common_keyframes": [],
        "desc": "", "digital_human_template_group_id": "",
        "enable_adjust": False, "enable_adjust_mask": False,
        "enable_color_correct_adjust": False, "enable_color_curves": True,
        "enable_color_match_adjust": False, "enable_color_wheels": True,
        "enable_hsl": False, "enable_hsl_curves": True, "enable_lut": True,
        "enable_mask_shadow": False, "enable_mask_stroke": False,
        "enable_smart_color_adjust": False, "enable_video_mask": False,
        "extra_material_refs": [], "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": seg_id, "intensifies_audio": False,
        "is_loop": False, "is_placeholder": False, "is_tone_modify": False,
        "keyframe_refs": [], "last_nonzero_volume": 1.0, "lyric_keyframes": None,
        "material_id": mat_id, "raw_segment_id": "",
        "render_index": render_index,
        "render_timerange": {"duration": 0, "start": 0},
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0
        },
        "reverse": False, "source": "segmentsourcenormal",
        "source_timerange": {"duration": duration_mu, "start": source_start},
        "speed": 1.0, "state": 0,
        "target_timerange": {"duration": duration_mu, "start": target_start},
        "template_id": "", "template_scene": "default",
        "track_attribute": 0, "track_render_index": render_index,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True, "volume": 1.0
    }

def make_text_material(txt_id, text_content):
    content_obj = {
        "styles": [{
            "fill_color": "#FFFFFF",
            "font": {"id": "", "path": "C:/Windows/Fonts/malgun.ttf"},
            "range": [0, len(text_content)],
            "size": 8.0,
            "stroke_color": "#000000",
            "stroke_width": 0.04,
            "bold": False, "italic": False, "underline": False
        }],
        "text": text_content
    }
    return {
        "add_type": 0, "alignment": 1,
        "background_alpha": 1.0, "background_color": "", "background_fill": "",
        "background_height": 0.14, "background_horizontal_offset": 0.0,
        "background_round_radius": 0.0, "background_style": 0,
        "background_vertical_offset": 0.0, "background_width": 0.14,
        "base_content": "", "bold_width": 0.0,
        "border_alpha": 1.0, "border_color": "", "border_mode": 0, "border_width": 0.08,
        "caption_template_info": {
            "category_id": "", "category_name": "", "effect_id": "",
            "is_new": False, "path": "", "request_id": "", "resource_id": "",
            "resource_name": "", "source_platform": 0
        },
        "check_flag": 7, "combo_info": {"text_templates": []},
        "content": json.dumps(content_obj, ensure_ascii=False),
        "current_words": "", "cutoff_postfix": "",
        "enable_path_typesetting": False,
        "fixed_height": -1.0, "fixed_width": -1.0,
        "font_category_id": "", "font_category_name": "",
        "font_id": "", "font_name": "", "font_path": "C:/Windows/Fonts/malgun.ttf",
        "font_resource_id": "", "font_size": 8.0,
        "font_source_platform": 0, "font_team_id": "",
        "font_third_resource_id": "", "font_title": "", "font_url": "",
        "fonts": [], "force_apply_line_max_width": False,
        "global_alpha": 1.0, "group_id": "",
        "has_shadow": False, "id": txt_id,
        "initial_scale": 1.0, "inner_padding": -1.0,
        "is_batch_replace": False, "is_lyric_effect": False,
        "is_rich_text": False, "is_words_linear": False,
        "italic_degree": 0, "ktv_color": "",
        "language": "", "layer_weight": 1,
        "letter_spacing": 0.0, "line_feed": 1,
        "line_max_width": 0.82, "line_spacing": 0.02,
        "lyric_group_id": "",
        "lyrics_template": {"aspect_ratio_type": -1, "lyric_effects": [], "name": ""},
        "multi_language_current": "none",
        "name": text_content[:20],
        "offset_on_path": 0.0, "oneline_cutoff": False, "operation_type": 0,
        "original_size": [],
        "preset_category": "", "preset_category_id": "", "preset_has_set_alignment": False,
        "preset_id": "", "preset_index": 0, "preset_name": "",
        "punc_model": "", "recognize_model": "", "recognize_task_id": "",
        "recognize_text": "", "recognize_type": 0,
        "relevance_segment": [],
        "shadow_alpha": 0.9, "shadow_angle": -45.0, "shadow_color": "",
        "shadow_distance": 0.0, "shadow_point": {"x": 0.6363961030678928, "y": -0.6363961030678928},
        "shadow_smoothing": 0.45,
        "shadow_thickness_projection_angle": 0.0,
        "shadow_thickness_projection_distance": 0.0,
        "shadow_thickness_projection_enable": False,
        "shape_clip_x": False, "shape_clip_y": False,
        "single_char_bg_alpha": 1.0, "single_char_bg_color": "",
        "single_char_bg_enable": False, "single_char_bg_height": 0.0,
        "single_char_bg_horizontal_offset": 0.0, "single_char_bg_round_radius": 0.0,
        "single_char_bg_vertical_offset": 0.0, "single_char_bg_width": 0.0,
        "source_from": "", "ssml_content": "",
        "style_name": "", "sub_template_id": "", "sub_type": "",
        "subtitle_keywords": None, "subtitle_keywords_config": None,
        "subtitle_template_original_fontsize": 0.0,
        "text_alpha": 1.0, "text_color": "#FFFFFF",
        "text_curve": None,
        "text_exceeds_path_process_type": 0,
        "text_loop_on_path": False,
        "text_preset_resource_id": "",
        "text_size": 30, "text_to_audio_ids": [],
        "text_typesetting_path_index": 0,
        "text_typesetting_paths": [], "text_typesetting_paths_file": "",
        "translate_original_text": "", "tts_auto_update": False,
        "type": "text", "typesetting": 0,
        "underline": False, "underline_offset": 0.22, "underline_width": 0.05,
        "use_effect_default_color": True,
        "words": {"end_time": [], "start_time": [], "text": []}
    }

def make_text_segment(seg_id, mat_id, duration_mu, target_start, render_index=0):
    return {
        "caption_info": None, "cartoon": False,
        "clip": {
            "alpha": 1.0,
            "flip": {"horizontal": False, "vertical": False},
            "rotation": 0.0,
            "scale": {"x": 1.0, "y": 1.0},
            "transform": {"x": 0.0, "y": 0.7}  # 화면 하단 70% 위치
        },
        "color_correct_alg_result": "", "common_keyframes": [],
        "desc": "", "digital_human_template_group_id": "",
        "enable_adjust": False, "enable_adjust_mask": False,
        "enable_color_correct_adjust": False, "enable_color_curves": True,
        "enable_color_match_adjust": False, "enable_color_wheels": True,
        "enable_hsl": False, "enable_hsl_curves": True, "enable_lut": True,
        "enable_mask_shadow": False, "enable_mask_stroke": False,
        "enable_smart_color_adjust": False, "enable_video_mask": False,
        "extra_material_refs": [], "group_id": "",
        "hdr_settings": {"intensity": 1.0, "mode": 1, "nits": 1000},
        "id": seg_id, "intensifies_audio": False,
        "is_loop": False, "is_placeholder": False, "is_tone_modify": False,
        "keyframe_refs": [], "last_nonzero_volume": 1.0, "lyric_keyframes": None,
        "material_id": mat_id, "raw_segment_id": "",
        "render_index": render_index,
        "render_timerange": {"duration": 0, "start": 0},
        "responsive_layout": {
            "enable": False, "horizontal_pos_layout": 0,
            "size_layout": 0, "target_follow": "", "vertical_pos_layout": 0
        },
        "reverse": False, "source": "segmentsourcenormal",
        "source_timerange": {"duration": duration_mu, "start": 0},
        "speed": 1.0, "state": 0,
        "target_timerange": {"duration": duration_mu, "start": target_start},
        "template_id": "", "template_scene": "default",
        "track_attribute": 0, "track_render_index": render_index,
        "uniform_scale": {"on": True, "value": 1.0},
        "visible": True, "volume": 1.0
    }

@app.route('/api/create_draft', methods=['POST'])
def create_draft():
    try:
        data = request.json
        print("\n" + "="*50)
        print("[서버] 편집 요청 수신")

        # 1. 데이터 파싱
        desc = data.get("params", {}).get("description", "")
        ai_plan = extract_json(desc) or data

        # 2. 프로젝트 폴더 생성 (템플릿 복사)
        timestamp = datetime.now().strftime("%H%M%S")
        draft_name = f"Reaction_{timestamp}_{str(uuid.uuid4())[:4]}"
        new_draft_dir = os.path.join(OUTPUT_BASE_DIR, draft_name)

        if os.path.exists(TEMPLATE_DIR):
            shutil.copytree(TEMPLATE_DIR, new_draft_dir)
        else:
            os.makedirs(new_draft_dir, exist_ok=True)

        # 3. 템플릿 draft_content.json 로드 (캡컷 호환 구조 보존)
        content_path = os.path.join(new_draft_dir, "draft_content.json")
        if os.path.exists(content_path):
            with open(content_path, 'r', encoding='utf-8') as f:
                content_info = json.load(f)
        else:
            content_info = {"materials": {}, "tracks": []}

        # 4. materials 초기화 (video/text만 비우고 나머지 유지)
        if "materials" not in content_info:
            content_info["materials"] = {}
        content_info["materials"]["videos"] = []
        content_info["materials"]["texts"] = []

        # 5. tracks에서 video/text 트랙의 segments 비우기
        video_track = None
        text_track = None
        kept_tracks = []
        for track in content_info.get("tracks", []):
            if track.get("type") == "video" and video_track is None:
                track["segments"] = []
                video_track = track
                kept_tracks.append(track)
            elif track.get("type") == "text" and text_track is None:
                track["segments"] = []
                text_track = track
                kept_tracks.append(track)
            elif track.get("type") not in ("video", "text"):
                kept_tracks.append(track)
        # 중복 video/text 트랙 제거 (템플릿에 여러 개 있을 경우)
        content_info["tracks"] = kept_tracks

        # 트랙이 없으면 새로 생성
        if video_track is None:
            video_track = {"attribute": 0, "flag": 0, "id": str(uuid.uuid4()),
                           "is_default_name": True, "name": "", "segments": [], "type": "video"}
            content_info.setdefault("tracks", []).append(video_track)
        if text_track is None:
            text_track = {"attribute": 0, "flag": 0, "id": str(uuid.uuid4()),
                          "is_default_name": True, "name": "", "segments": [], "type": "text"}
            content_info["tracks"].append(text_track)

        # 6. clips 데이터 처리
        MU = 1_000_000
        cur_time = 0
        path_map = {}

        raw_clips = ai_plan.get("clips", [])
        if not raw_clips and "videos" in ai_plan:
            texts = ai_plan.get("texts", [])
            for i, v in enumerate(ai_plan.get("videos", [])):
                t_content = texts[i].get("content", "") if i < len(texts) else ""
                raw_clips.append({
                    "path": v.get("path", ""),
                    "start_time": v.get("start_time", 0),
                    "end_time": v.get("end_time", 5),
                    "content": t_content
                })

        print(f"[서버] 클립 수: {len(raw_clips)}")

        for idx, clip in enumerate(raw_clips):
            v_path = clip.get("path", "").replace("\\", "/")
            if not os.path.exists(v_path):
                print(f"  [경고] 파일 없음: {v_path}")
                continue

            # 비디오 material 등록 (동일 파일은 재사용)
            if v_path not in path_map:
                vid_dur, vid_w, vid_h = get_video_metadata(v_path)
                mid = str(uuid.uuid4()).upper()
                content_info["materials"]["videos"].append(
                    make_video_material(mid, v_path, vid_dur, vid_w, vid_h)
                )
                path_map[v_path] = mid

            v_mid = path_map[v_path]
            start = int(float(clip.get("start_time", 0)) * MU)
            end   = int(float(clip.get("end_time",   0)) * MU)
            dur   = end - start
            if dur <= 0:
                continue

            # 비디오 세그먼트
            video_track["segments"].append(
                make_video_segment(
                    seg_id=str(uuid.uuid4()).upper(),
                    mat_id=v_mid,
                    source_start=start,
                    duration_mu=dur,
                    target_start=cur_time,
                    render_index=idx
                )
            )

            # 자막 세그먼트
            txt = clip.get("content", "")
            if txt:
                tmid = str(uuid.uuid4()).upper()
                content_info["materials"]["texts"].append(
                    make_text_material(tmid, txt)
                )
                text_track["segments"].append(
                    make_text_segment(
                        seg_id=str(uuid.uuid4()).upper(),
                        mat_id=tmid,
                        duration_mu=dur,
                        target_start=cur_time,
                        render_index=idx
                    )
                )

            cur_time += dur

        # 7. 전체 duration 업데이트
        content_info["duration"] = cur_time

        with open(content_path, 'w', encoding='utf-8') as f:
            json.dump(content_info, f, ensure_ascii=False, indent=2)

        # 8. draft_meta_info.json 업데이트
        meta_path = os.path.join(new_draft_dir, "draft_meta_info.json")
        meta_info = {
            "draft_name": draft_name,
            "draft_id": str(uuid.uuid4()).upper(),
            "draft_fold_path": new_draft_dir.replace("\\", "/"),
            "draft_json_file": content_path.replace("\\", "/"),
            "draft_root_path": OUTPUT_BASE_DIR.replace("\\", "/"),
            "tm_duration": cur_time,
            "tm_draft_create": int(datetime.now().timestamp() * 1_000_000),
            "tm_draft_modified": int(datetime.now().timestamp() * 1_000_000),
            "draft_type": "",
            "draft_timeline_materials_size": 0,
            "cloud_draft_sync": False,
            "draft_is_ai_shorts": False,
            "draft_is_invisible": False
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta_info, f, ensure_ascii=False, indent=2)

        print(f"[성공] 프로젝트 생성: {new_draft_dir}")
        print(f"  - 비디오 클립: {len(video_track['segments'])}개")
        print(f"  - 자막: {len(text_track['segments'])}개")
        return jsonify({"status": "success", "path": new_draft_dir}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    print(f"서버 가동 중 (결과폴더: {OUTPUT_BASE_DIR})")
    app.run(host='0.0.0.0', port=9000)
