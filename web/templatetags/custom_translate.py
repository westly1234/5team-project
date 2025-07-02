# web/templatetags/custom_translate.py

from django import template
from web.utils import t as translate_text
from django.utils.functional import lazy

register = template.Library()

@register.simple_tag
def t(key, **kwargs):
    return translate_text(key, **kwargs)

def t_lazy(key, **kwargs):
    return lazy(lambda: translate_text(key, **kwargs), str)()