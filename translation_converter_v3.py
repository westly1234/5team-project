import os
import re
import json
from pathlib import Path

# --- 설정 ---
# ⚠️ 중요: HTML 템플릿이 들어있는 모든 폴더 경로를 여기에 추가하세요.
# 프로젝트 루트를 기준으로 경로를 지정합니다.
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIRS = [
    # 예시: 각 앱 내부의 templates 폴더
    BASE_DIR / 'web' / 'templates',
    BASE_DIR / 'accounts' / 'templates',
    BASE_DIR / 'chatbot' / 'templates',
    BASE_DIR / 'diet' / 'templates',
    BASE_DIR / 'edit' / 'templates',
    BASE_DIR / 'music' / 'templates',
    BASE_DIR / 'place' / 'templates',
    BASE_DIR / 'routine' / 'templates',
    BASE_DIR / 'store' / 'templates',
    # 예시: 프로젝트 루트의 templates 폴더
    # BASE_DIR / 'templates', 
]

# 미리 준비된 한국어 JSON 파일 경로
KOREAN_JSON_PATH = BASE_DIR / 'locales' / 'ko.json'
# --- 설정 끝 ---

def load_korean_json(path):
    if not path.exists():
        print(f"❌ 오류: '{path}' 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
        return None
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    sorted_items = sorted(data.items(), key=lambda item: len(item[1]), reverse=True)
    value_to_key_map = {value: key for key, value in sorted_items}
    print(f"✅ '{path}' 로드 완료. {len(value_to_key_map)}개의 번역 항목을 찾았습니다.")
    return value_to_key_map

def create_regex_from_keys(text_list):
    escaped_texts = [re.escape(text) for text in text_list]
    # > 와 < 사이, 또는 태그 속성이 아닌 순수 텍스트를 더 잘 찾기 위한 개선된 정규식
    # Django 템플릿 변수나 태그는 제외
    pattern = r'>\s*(' + '|'.join(escaped_texts) + r')\s*<'
    return re.compile(pattern)

def process_file(file_path, value_to_key_map, regex_pattern):
    print(f"🔄 처리 중: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        def replacement_func(match):
            found_text = match.group(1).strip()
            if found_text in value_to_key_map:
                key = value_to_key_map[found_text]
                # 변환된 키에 ' 또는 " 가 포함되어 있으면 템플릿 오류가 날 수 있으므로 확인
                if "'" in key or '"' in key:
                    print(f"  ⚠️ 경고: 키 '{key}'에 따옴표가 포함되어 있어 건너뜁니다. 수동으로 처리해주세요.")
                    return match.group(0)
                return f"> {{% t '{key}' %}} <"
            return match.group(0)

        new_content, count = regex_pattern.subn(replacement_func, content)
        
        if count > 0:
            print(f"  ✅ {count}개의 항목을 변환했습니다. 파일을 저장합니다.")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        else:
            print("  - 변환할 항목이 없습니다.")

    except Exception as e:
        print(f"  ❌ 오류 발생: {file_path} - {e}")

def main():
    print("="*50)
    print("ko.json 기반 Django 템플릿 변환 스크립트 (v3)를 시작합니다.")
    
    value_to_key_map = load_korean_json(KOREAN_JSON_PATH)
    if not value_to_key_map:
        return
    
    korean_texts = list(value_to_key_map.keys())
    combined_regex = create_regex_from_keys(korean_texts)

    for template_dir in TEMPLATE_DIRS:
        if not template_dir.is_dir():
            print(f"  - 경고: '{template_dir}' 폴더를 찾을 수 없습니다. 건너뜁니다.")
            continue
            
        print("\n" + "="*50)
        print(f"🔍 '{template_dir}' 폴더에서 HTML 파일을 찾습니다...")
        for root, _, files in os.walk(template_dir):
            for filename in files:
                if filename.endswith(".html"):
                    process_file(Path(root) / filename, value_to_key_map, combined_regex)

    print("\n" + "="*50)
    print("모든 작업이 완료되었습니다.")


if __name__ == "__main__":
    main()