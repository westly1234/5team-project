# web/urls.py - 이렇게 수정해주세요!
from django.urls import path
from . import views  # 'views'로 import 합니다.

app_name = 'web'

urlpatterns = [
    path('', views.home, name='home'),
    path('health/', views.health_page_view, name='health_page'),
    path('services/', views.services_page, name='services'), 
    # 'signup/' URL에 대해 'views.auth_signup_view' 함수를 연결합니다.
    path('service/workout/', views.workout_plan_view, name='workout_plan'),
    path('service/diet/', views.diet_management_view, name='diet_management'),
    path('service/places/', views.nearby_places_view, name='nearby_places'),
    path('service/chatbot/', views.ai_chatbot_view, name='ai_chatbot'),
    path('start-trial/', views.start_trial, name='start_trial'),
]