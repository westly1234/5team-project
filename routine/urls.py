from django.urls import path
from . import views

app_name = 'routine' # URL을 템플릿에서 쉽게 부르기 위한 네임스페이스

urlpatterns = [
    # http://.../routine/ -> routine_select_view 함수 실행
    path('', views.routine_select_view, name='select'),
    
    # http://.../routine/my-routines/ -> my_routines_view 함수 실행
    path('my-routines/', views.my_routines_view, name='my_routines'),
    
    # http://.../routine/gpt-plan/ -> gpt_plan_view 함수 실행
    path('gpt-plan/', views.gpt_plan_view, name='gpt_plan'),
    
    # http://.../routine/custom-plan/ -> custom_plan_view 함수 실행
    path('custom-plan/', views.custom_plan_view, name='custom_plan'),
    
    # API 엔드포인트
    # http://.../routine/api/exercises/ -> exercise_api 함수 실행
    path('api/exercises/', views.exercise_api, name='api_exercises'),
    # 예: /routine/edit/5/
    path('edit/<int:routine_id>/', views.edit_routine_view, name='edit_routine'),
    # 예: /routine/delete/5/
    path('delete/<int:routine_id>/', views.delete_routine_view, name='delete_routine'),
    path('api/youtube-search/', views.youtube_search_api, name='api_youtube_search'), 
]