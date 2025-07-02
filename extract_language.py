# extract_language.py (최종 완성 버전: Python + HTML 전체 스캔, 삭제 기능 없음)

import os
import re
import json
import time
from tqdm import tqdm

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
import openai

# --- 설정 ---
SCAN_TARGET_APPS = ['accounts', 'achievements', 'chatbot', 'diet', 'routine', 'web', 'store', 'place', 'music']
OUTPUT_DIR = 'locales'
KO_JSON_FILE = os.path.join(OUTPUT_DIR, 'ko.json')
TARGET_LANGUAGES = ['en', 'es']
MIN_TEXT_LENGTH = 2
CHUNK_SIZE = 40
MAX_RETRIES = 3

# OpenAI 클라이언트 초기화
try:
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
except Exception as e:
    print(f"🚨 OpenAI API 키 설정 오류: {e}")
    client = None

# --- 번역 함수 (안정성 강화된 최종 버전) ---
def translate_text_list_with_gpt(text_list, target_lang):
    if not client:
        print("🚨 GPT 클라이언트가 초기화되지 않아 번역을 건너뜁니다.")
        return None
        
    language_map = {'en': 'English', 'es': 'Spanish'}
    target_language_name = language_map.get(target_lang, target_lang.capitalize())
    
    prompt = f"""
You are a professional translator for a health and fitness app.
Your task is to translate each string in the following JSON array from Korean to {target_language_name}.
**Instructions:**
- Maintain the original order of the strings.
- Your response must be a valid JSON object containing a single key "translations" which holds the array of translated strings.
- For example: {{"translations": ["translated text 1", "translated text 2"]}}
**Input to translate:**
{json.dumps(text_list, ensure_ascii=False, indent=2)}
"""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], temperature=0.1, response_format={"type": "json_object"}, timeout=60)
            content = response.choices[0].message.content.strip()
            response_data = json.loads(content)
            translated_list = response_data.get("translations")
            if translated_list and isinstance(translated_list, list) and len(translated_list) == len(text_list):
                return translated_list
            else:
                print(f"  ⚠️ 번역 결과 형식 또는 길이 불일치 (시도 {attempt + 1}/{MAX_RETRIES}).")
        except Exception as e:
            print(f"🚨 GPT API 오류 (시도 {attempt + 1}/{MAX_RETRIES}): {e}")
        if attempt < MAX_RETRIES - 1:
            time.sleep(3 * (attempt + 1))
            
    return None

# --- 메인 실행 함수 (수정됨) ---
def main():
    print("\n--- Django 프로젝트 문자열 '추가' 및 번역 관리 시작 ---")
    
    # 1. 프로젝트 파일에서 모든 키 추출
    project_keys = set()
    
    # ✅ 추출을 위한 정규식 패턴 정의
    # Python 또는 JavaScript 코드용: t('...')
    t_pattern_script_or_py = re.compile(r"t\('([^']*)'\)")
    # Django 템플릿 태그용: {% t '...' %}
    t_pattern_django_tag = re.compile(r"{%\s*t\s*'([^']*)'\s*%}")
    # HTML에서 <script> 블록을 찾기 위한 정규식
    script_block_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL)

    print("🔍 프로젝트 파일(.py, .html) 스캔 중...")
    for app_name in tqdm(SCAN_TARGET_APPS, desc="앱 스캔"):
        app_path = os.path.join(settings.BASE_DIR, app_name)
        if not os.path.exists(app_path): continue
        for root, _, files in os.walk(app_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f: content = f.read()
                    
                    found_texts = []
                    if file.endswith('.py'):
                        # Python 파일: 파일 전체에서 t('...') 검색
                        found_texts.extend(t_pattern_script_or_py.findall(content))
                    elif file.endswith('.html'):
                        # ✅ HTML 파일: 스크립트 안과 밖을 모두 검색
                        # 1. <script> 블록 내부에서는 t('...') 패턴을 찾음
                        script_blocks = script_block_pattern.findall(content)
                        for block in script_blocks:
                            found_texts.extend(t_pattern_script_or_py.findall(block))
                        
                        # 2. <script> 블록을 제외한 나머지 부분에서는 {% t '...' %} 패턴을 찾음
                        non_script_content = script_block_pattern.sub('', content)
                        found_texts.extend(t_pattern_django_tag.findall(non_script_content))
                            
                    for text in found_texts:
                        clean_text = text.strip()
                        if len(clean_text) >= MIN_TEXT_LENGTH: project_keys.add(clean_text)
                except Exception: continue
    print(f"\n✅ 총 {len(project_keys)}개의 고유 문자열을 코드에서 추출했습니다.\n")

    # 2. ko.json 파일을 '마스터' 파일로 업데이트 (추가만 수행)
    try:
        with open(KO_JSON_FILE, 'r', encoding='utf-8') as f:
            master_ko_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        master_ko_data = {}
    
    # ✅ 삭제 로직 없이, 추가 로직만 수행합니다.
    added_ko_count = 0
    for key in sorted(list(project_keys)):
        if key not in master_ko_data:
            master_ko_data[key] = key
            added_ko_count += 1
    
    with open(KO_JSON_FILE, 'w', encoding='utf-8') as f:
        sorted_ko_data = dict(sorted(master_ko_data.items()))
        json.dump(sorted_ko_data, f, ensure_ascii=False, indent=4)
    print(f"📖 '{KO_JSON_FILE}' 업데이트 완료. {added_ko_count}개의 새로운 항목이 추가되었습니다.\n")

    # 3. 다른 언어 파일을 'ko.json' 기준으로 동기화 (추가만 수행)
    # ✅ 최종 업데이트된 ko.json을 기준으로 삼습니다.
    ko_keys = set(sorted_ko_data.keys())

    for lang in TARGET_LANGUAGES:
        lang_file = os.path.join(OUTPUT_DIR, f"{lang}.json")
        try:
            with open(lang_file, 'r', encoding='utf-8') as f: existing_lang_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): existing_lang_data = {}

        # ✅ ko.json에 있는데, 해당 언어 파일에는 없는 키만 번역 대상으로 선정
        keys_to_translate = sorted(list(ko_keys - set(existing_lang_data.keys())))
        
        if not keys_to_translate:
            print(f"🌍 '{lang}.json': 모든 항목이 'ko.json'과 동기화되어 있습니다. 건너뜁니다.")
        else:
            print(f"🌍 '{lang}.json': 'ko.json' 기준으로 {len(keys_to_translate)}개의 항목 번역을 시작합니다...")
            # 번역이 성공할 때마다 기존 데이터에 추가
            for i in tqdm(range(0, len(keys_to_translate), CHUNK_SIZE), desc=f"'{lang}' 번역 중"):
                chunk_keys = keys_to_translate[i:i + CHUNK_SIZE]
                translated_values = translate_text_list_with_gpt(chunk_keys, lang)
                if translated_values:
                    for key, value in zip(chunk_keys, translated_values):
                        existing_lang_data[key] = value
                else:
                    print(f"  ❌ 최종 실패: '{lang}' 언어의 일부 번역에 실패했습니다. 해당 청크는 건너뜁니다.")
                if len(keys_to_translate) > CHUNK_SIZE: time.sleep(1)
            
            # 최종적으로 업데이트된 내용을 파일에 저장
            with open(lang_file, 'w', encoding='utf-8') as f:
                final_sorted_data = dict(sorted(existing_lang_data.items()))
                json.dump(final_sorted_data, f, ensure_ascii=False, indent=4)
            print(f"   - '{lang_file}' 업데이트 완료. 현재 총 {len(final_sorted_data)}개의 키가 있습니다.\n")

    print("🎉 모든 번역 작업이 성공적으로 완료되었습니다!")

# --- 스크립트 실행 진입점 ---
if __name__ == "__main__":
    print("=" * 60)
    print("!!주의!! 이 스크립트는 'locales' 폴더의 파일을 직접 수정합니다.")
    print("실행 전 반드시 해당 폴더를 백업해두는 것을 권장합니다.")
    print("=" * 60)
    confirm = input("계속 진행하시겠습니까? (y/n): ")
    if confirm.lower() == 'y':
        main()
    else:
        print("작업을 취소했습니다.")