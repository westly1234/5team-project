# store/admin.py

from django.contrib import admin
from .models import Brand, Tag, Review, Product, BrandCategory

# ✅ 새로 만든 BrandCategory 모델을 관리자 페이지에 등록합니다.
@admin.register(BrandCategory)
class BrandCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    # ✅ [핵심 수정] list_display와 list_filter를 새로운 'categories' 필드에 맞게 변경
    list_display = ('name', 'display_categories', 'get_average_rating_display', 'is_featured', 'created_at')
    list_filter = ('categories', 'is_featured', 'tags') # 'category' -> 'categories'
    search_fields = ('name', 'description', 'detailed_description')
    
    # ✅ 다대다 관계를 관리하기 편한 UI로 변경 (filter_horizontal)
    filter_horizontal = ('categories', 'tags', 'favorited_by')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'link', 'is_featured')
        }),
        # ✅ 'category'를 'categories'로 변경
        ('카테고리 및 태그', {
            'fields': ('categories', 'tags')
        }),
        ('설명', {
            'fields': ('description', 'detailed_description')
        }),
        ('이미지 및 프로모션', {
            'fields': ('thumbnail', 'promotion_info')
        }),
        ('연관 데이터 (선택)', {
            'classes': ('collapse',),
            'fields': ('favorited_by',),
        }),
    )
    
    # ✅ [핵심 추가] 다대다 관계인 카테고리들을 보기 좋게 문자열로 만들어주는 함수
    @admin.display(description='카테고리')
    def display_categories(self, obj):
        # obj.categories.all()로 해당 브랜드에 연결된 모든 카테고리를 가져옴
        return ", ".join([category.name for category in obj.categories.all()])

    @admin.display(description='평균 평점')
    def get_average_rating_display(self, obj):
        avg_rating = obj.get_average_rating()
        return f"{avg_rating:.2f}점" if avg_rating > 0 else "리뷰 없음"

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ('name',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('brand', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('brand__name', 'user__username', 'content')
    autocomplete_fields = ('brand', 'user')

admin.site.register(Product)