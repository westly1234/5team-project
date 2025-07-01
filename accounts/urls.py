from django.urls import path
from . import views
from django.http import HttpResponse
from django.contrib.auth import views as auth_views  # 로그인과 로그아웃을 위한 뷰
from django.contrib.auth.views import LogoutView
from django.contrib.auth import views as auth_views

app_name = 'accounts'

def home(request):
    return HttpResponse("여기는 Accounts 앱입니다.")

urlpatterns = [
    path('', home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(), name='login'),   # 로그인
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('my-titles/', views.get_my_titles, name='my_titles'),
    path('set-active-title/', views.set_my_active_title, name='set_active_title'),
    path('find-username/', views.find_username_view, name='find_username'),
    path('password_reset/', views.custom_password_reset_view, name='password_reset'),
    path('password_reset/done/', views.custom_password_reset_done_view, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.custom_password_reset_confirm_view, name='password_reset_confirm'),
    path('reset/done/', views.custom_password_reset_complete_view, name='password_reset_complete'),
    path('save-survey/', views.save_survey_view, name='save_survey_view'),
    path('check-username/', views.check_username, name='check_username'),
]