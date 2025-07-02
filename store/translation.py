from modeltranslation.translator import register, TranslationOptions
from .models import (BrandCategory, Tag) # 필요한 모델만 import 합니다.

# 1. 브랜드 카테고리 번역 등록
@register(BrandCategory)
class BrandCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)

# 2. 태그 번역 등록
@register(Tag)
class TagTranslationOptions(TranslationOptions):
    fields = ('name',)