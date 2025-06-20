# store/urls.py

from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # 기존 페이지
    path('', views.store_home_view, name='home'),
    
    # 상세 정보 API (기존)
    path('api/brand/<int:brand_id>/', views.brand_detail_api, name='brand_detail_api'),
    
    # ✅ [기능 추가] 새로운 API 및 페이지 경로들
    path('api/brand/<int:brand_id>/toggle_favorite/', views.toggle_favorite_api, name='toggle_favorite_api'),
    path('api/brand/<int:brand_id>/add_review/', views.add_review_api, name='add_review_api'),
    path('api/compare/', views.compare_brands_api, name='compare_brands_api'),
    
    # 브랜드 찾기 퀴즈
    path('finder/', views.brand_finder_view, name='finder'),
    
    # 브랜드 비교 결과 페이지
    path('compare/', views.compare_page_view, name='compare_page'),
]