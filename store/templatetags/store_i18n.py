# store/templatetags/store_i18n.py

import json
from django import template
from django.utils import translation
from django.conf import settings
from django.utils.safestring import mark_safe
from pathlib import Path

register = template.Library()

def _get_translation_dict():
    try:
        current_language = translation.get_language() or 'ko'
        file_path = Path(settings.BASE_DIR) / 'locales' / f'{current_language}.json'
        if not file_path.exists():
            return {}
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return {}

@register.simple_tag
def t(key, **kwargs):
    translations = _get_translation_dict()
    translated_string = translations.get(key, key)
    if kwargs:
        translated_string = translated_string.format(**kwargs)
    return translated_string

@register.simple_tag
def get_js_translations():
    translations_dict = _get_translation_dict()
    return mark_safe(json.dumps(translations_dict))