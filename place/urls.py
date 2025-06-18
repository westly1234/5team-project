from django.urls import path
from . import views

app_name = 'place'  # URL 네임스페이스 설정

urlpatterns = [
    path('', views.place_search_view, name='search'),
]