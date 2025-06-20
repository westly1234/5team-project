# achievements/urls.py
from django.urls import path
from . import views

app_name = 'achievements'

urlpatterns = [
    # 내 업적 목록을 보여주는 페이지 (예: /achievements/)
    path('', views.achievements_list, name='list'),

    # 대표 칭호를 설정하는 URL (예: /achievements/set-title/5/)
    path('set-title/<int:user_achievement_id>/', views.set_active_title, name='set_active_title'),
]