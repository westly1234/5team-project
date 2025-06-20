from django.template.defaulttags import register

@register.filter
def get_item(dictionary, key):
    """템플릿에서 딕셔너리 값에 변수 키로 접근하기 위한 필터"""
    return dictionary.get(key)
