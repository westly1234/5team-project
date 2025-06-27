# web/utils.py

import json
from django.conf import settings
from django.utils import translation
from django.utils.safestring import mark_safe

# 번역 데이터를 캐싱하여 파일 I/O를 줄이는 역할
_translations = {}

def load_translations(lang_code):
    # 이미 메모리에 로드된 언어는 다시 읽지 않음 (효율성!)
    if lang_code in _translations:
        return _translations[lang_code]

    # 기본 언어는 'ko'로 설정
    if not lang_code:
        lang_code = 'ko'

    # locales/en.json 같은 파일 경로를 찾음
    file_path = settings.BASE_DIR / 'locales' / f'{lang_code}.json'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            translations_data = json.load(f)
            _translations[lang_code] = translations_data
            return translations_data
    except FileNotFoundError:
        # 만약 해당 언어 파일이 없으면, 한국어 파일이라도 불러옴
        if lang_code != 'ko':
            return load_translations('ko')
        return {} # 한국어 파일도 없으면 빈 데이터 반환

def t(key, **kwargs):
    # Django의 현재 활성화된 언어 코드를 가져옴 (예: 'ko', 'en')
    current_language = translation.get_language()
    
    # 해당 언어의 번역 데이터를 로드
    translations = load_translations(current_language)
    
    # 1. key에 해당하는 번역문을 찾음
    # 2. 번역문이 없으면, key 자체를 반환 (번역이 누락되어도 화면이 깨지지 않게)
    translated_string = translations.get(key, key)
    
    # 3. placeholder 변수 치환 (예: "안녕하세요, {name}님!")
    if kwargs:
        translated_string = translated_string.format(**kwargs)

    # 4. HTML 태그가 포함될 수 있으므로 안전하게 처리
    return mark_safe(translated_string)