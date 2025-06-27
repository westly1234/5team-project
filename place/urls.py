from django.urls import path
from . import views

app_name = 'place'  # URL 네임스페이스 설정

urlpatterns = [
    path('', views.place_search_view, name='search'),
    path('log-search/', views.log_place_search_api, name='log_search'),
]