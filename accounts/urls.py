from django.urls import path
from . import views
from django.http import HttpResponse
from django.contrib.auth import views as auth_views  # 로그인과 로그아웃을 위한 뷰
from django.contrib.auth.views import LogoutView

app_name = 'accounts'

def home(request):
    return HttpResponse("여기는 Accounts 앱입니다.")

urlpatterns = [
    path('', home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(), name='login'),   # 로그인
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
]