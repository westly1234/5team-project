# web/urls.py - 전체 코드를 이걸로 교체하세요.

from django.urls import path
from . import views

app_name = 'web'  # 이 앱의 그룹 이름을 'web'으로 지정

urlpatterns = [
    path('', views.home, name='home'),
    # /web/services/
    path('services/', views.services_page, name='services'), 
    
    # /web/support/
    path('support/', views.support_view, name='support'),
    
    # /web/support/inquiry/
    path('inquiry/', views.inquiry_view, name='inquiry'), # URL을 web/inquiry/ 로 단순화

    # 나머지 web 관련 URL들
    path('health/', views.health_page_view, name='health_page'),
    path('service/workout/', views.workout_plan_view, name='workout_plan'),
    path('service/diet/', views.diet_management_view, name='diet_management'),
    path('service/places/', views.nearby_places_view, name='nearby_places'),
    path('service/chatbot/', views.ai_chatbot_view, name='ai_chatbot'),
    path('start-trial/', views.start_trial, name='start_trial'),
]