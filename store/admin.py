# store/admin.py

from django.contrib import admin
from .models import Product, Brand

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    # ✅ 리스트에 표시할 필드를 추가합니다.
    list_display = ('name', 'category', 'is_featured', 'link', 'created_at')
    # ✅ 필터링 옵션을 추가하여 관리를 쉽게 합니다.
    list_filter = ('category', 'is_featured')
    search_fields = ('name', 'short_description')
    # ✅ 관리자 페이지에서 직접 수정할 수 있는 필드
    list_editable = ('category', 'is_featured')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_link', 'created_at')
    search_fields = ('name', 'description')