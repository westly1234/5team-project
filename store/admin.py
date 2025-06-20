# store/admin.py

from django.contrib import admin
from .models import Brand, Tag, Review, Product

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_featured', 'promotion_info', 'created_at')
    list_filter = ('category', 'is_featured', 'tags')
    search_fields = ('name', 'description', 'detailed_description')
    # ManyToManyField를 관리자 페이지에서 편하게 선택할 수 있도록 해줍니다.
    filter_horizontal = ('tags', 'favorited_by')
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'link', 'is_featured')
        }),
        ('설명', {
            'fields': ('description', 'detailed_description')
        }),
        ('이미지 및 프로모션', {
            'fields': ('thumbnail', 'promotion_info')
        }),
        ('연관 데이터 (선택)', {
            'classes': ('collapse',),
            'fields': ('tags', 'favorited_by'),
        }),
    )

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('brand', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('brand__name', 'user__username', 'content')
    autocomplete_fields = ('brand', 'user') # ForeignKey 필드를 검색으로 찾기 쉽게 해줍니다.

# Product 모델도 등록합니다.
admin.site.register(Product)