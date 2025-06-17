# music/urls.py (새 파일)

from django.urls import path
from . import views

app_name = 'music'  # URL 네임스페이스 설정

urlpatterns = [
    path('', views.music_playlist_view, name='music_playlist'),
    path('api/ai-keywords/', views.get_ai_keywords, name='get_ai_keywords'),
]