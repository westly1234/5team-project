# store/urls.py (새 파일)

from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    path('', views.store_page_view, name='home'),
]