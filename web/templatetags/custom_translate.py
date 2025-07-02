from django import template
from web.utils import t as translate_text
from django.utils.functional import lazy

register = template.Library()

# 템플릿 태그: {% t "문자열" %}
@register.simple_tag
def t(key, **kwargs):
    return translate_text(key, **kwargs)

# 템플릿 필터: {{ "문자열"|t }}
@register.filter(name='t')
def translate_filter(value):
    return translate_text(value)

def t_lazy(key, **kwargs):
    return lazy(lambda: translate_text(key, **kwargs), str)()