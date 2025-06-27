# web/templatetags/custom_translate.py

from django import template
from web.utils import t as translate_text

register = template.Library()

@register.simple_tag
def t(key, **kwargs):
    return translate_text(key, **kwargs)