# diet/urls.py

from django.urls import path
from . import views

app_name = 'diet'

urlpatterns = [
    # 기존 URL
    path('analysis/', views.diet_analysis_view, name='diet_analysis'),
    path('result/<int:meal_id>/', views.diet_result_view, name='diet_result'),
    
    # 새로 추가된 대시보드 URL
    path('report/', views.diet_report_view, name='diet_report'),
    path('delete/<int:meal_id>/', views.delete_meal_view, name='delete_meal'),
]