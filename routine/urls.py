# routine/urls.py

from django.urls import path
from . import views

app_name = 'routine'

urlpatterns = [
    # 페이지 렌더링 URL
    path('', views.routine_select_view, name='select'),
    path('my-routines/', views.my_routines_view, name='my_routines'),
    # 예: /routine/plan/5/ -> 특정 루틴의 상세/수정 페이지
    path('plan/<int:routine_id>/', views.routine_plan_detail_view, name='routine_plan_detail'),

    # 처리/액션 URL
    path('gpt-plan/', views.gpt_plan_view, name='gpt_plan'),
    path('custom-plan/', views.custom_plan_view, name='custom_plan'),
    # 예: /routine/edit/5/ -> 루틴 수정 내용 저장
    path('edit/<int:routine_id>/', views.edit_routine_view, name='edit_routine'),
    # 예: /routine/delete/5/ -> 루틴 삭제
    path('delete/<int:routine_id>/', views.delete_routine_view, name='delete_routine'),
    
    # API URLs
    path('api/exercises/', views.exercise_api, name='api_exercises'),
    path('api/youtube-search/', views.youtube_search_api, name='api_youtube_search'),
]