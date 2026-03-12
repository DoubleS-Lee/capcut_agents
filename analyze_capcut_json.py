import json
import os

draft_dir = "D:\\00.Google CLI\\capcut_agents_260309\\reference\\com.lveditor.draft\\0305"
meta_path = os.path.join(draft_dir, "draft_meta_info.json")
content_path = os.path.join(draft_dir, "draft_content.json")

def print_structure(d, indent=0, max_level=3):
    if indent > max_level:
        return
    
    if isinstance(d, dict):
        for k, v in d.items():
            print("  " * indent + f"- {k} ({type(v).__name__})")
            if isinstance(v, (dict, list)):
                if k not in ["segments", "draft_materials"]: # 너무 긴 리스트 생략
                    print_structure(v, indent + 1, max_level)
    elif isinstance(d, list) and len(d) > 0:
        print("  " * indent + f"[List of {type(d[0]).__name__}]")
        print_structure(d[0], indent + 1, max_level)

print("=== draft_meta_info.json 구조 ===")
with open(meta_path, 'r', encoding='utf-8') as f:
    meta = json.load(f)
    print_structure(meta, max_level=1)

print("\n=== draft_content.json 구조 ===")
with open(content_path, 'r', encoding='utf-8') as f:
    content = json.load(f)
    print_structure(content, max_level=1)
    
print("\n=== 필수 버전 정보 ===")
print("meta_info draft_name:", meta.get("draft_name"))
print("meta_info draft_fold_path:", meta.get("draft_fold_path"))
print("meta_info draft_id:", meta.get("draft_id"))
print("content_info tracks count:", len(content.get("tracks", [])))
print("content_info materials keys:", list(content.get("materials", {}).keys()))
