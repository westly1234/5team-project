# store/urls.py

from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.store_page_view, name='home'),
    
    # ✅ [핵심 변경] 퀵 뷰 모달에 데이터를 제공할 API URL을 추가합니다.
    path('api/brand/<int:brand_id>/', views.brand_detail_api, name='brand_detail_api'),
]