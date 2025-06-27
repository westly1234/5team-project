from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # 페이지 URL
    path('', views.store_home_view, name='home'),
    path('compare/', views.compare_page_view, name='compare_page'),
    path('brand-finder/', views.brand_finder_view, name='brand_finder'),
    path('my-favorites/', views.favorite_brands_view, name='my_favorites'),

    # API URL
    path('api/brands/<int:brand_id>/detail/', views.brand_detail_api, name='brand_detail_api'),
    path('api/brands/<int:brand_id>/toggle_favorite/', views.toggle_favorite_api, name='toggle_favorite_api'),
    path('api/brands/<int:brand_id>/add_review/', views.add_review_api, name='add_review_api'),
    path('api/compare-brands/', views.compare_brands_api, name='compare_brands_api'),
    path('api/filter-brands/', views.filter_brands_api, name='filter_brands_api'),

    # ✅ 체형 분석 페이지와 API를 위한 URL 추가
    path('body-shape-analyzer/', views.body_shape_analyzer_view, name='body_shape_analyzer'),
    path('api/analyze-body-shape/', views.analyze_body_shape_api, name='analyze_body_shape_api'),
]
