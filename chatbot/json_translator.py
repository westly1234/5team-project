# chatbot/json_translator.py

import json
import os
from django.conf import settings

# 불러온 번역 데이터를 저장해두는 공간 (매번 파일을 읽지 않기 위해)
_translations_cache = {}

def _load_json_translations(lang_code: str):
    """캐시 또는 파일에서 특정 언어의 JSON 번역 데이터를 불러옵니다."""
    if lang_code in _translations_cache:
        return _translations_cache[lang_code]

    # settings.py의 LOCALE_PATHS를 사용하지 않고, locales 폴더를 직접 지정합니다.
    # 'locales' 폴더가 프로젝트 최상위 폴더에 있다고 가정합니다.
    file_path = os.path.join(settings.BASE_DIR, 'locales', f'{lang_code}.json')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _translations_cache[lang_code] = data
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # 파일이 없거나 JSON 형식이 잘못된 경우, 빈 데이터를 반환
        _translations_cache[lang_code] = {}
        return {}

def translate(key: str, lang_code: str):
    """
    주어진 키와 언어 코드를 사용해 .json 파일에서 번역된 문자열을 가져옵니다.
    """
    translations = _load_json_translations(lang_code)
    # 번역이 없으면 원본 키(한글)를 그대로 반환
    return translations.get(key, key)