from django.contrib import admin
from django.urls import path, include
from accounts import views as accounts_views
from web import views as web_views  # ✅ web 앱의 뷰를 불러올 때는 이렇게
from django.urls import path, include 
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path('save-survey/', accounts_views.save_survey_view, name='save_survey_ajax'),
    path('services/', web_views.services_page, name='services_page'),
    path('web/', include(('web.urls', 'web'), namespace='web')),
    path('music/', include('music.urls')), 
    path('place/', include('place.urls')),
    path('routine/', include('routine.urls')), 
    # 메인 페이지 및 기타 직접 연결되는 뷰
    path('', web_views.home, name='home'),
    path('diet/', include('diet.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('achievments', include('achievements.urls')),
    path('store/', include('store.urls')),
]

# 사용자가 업로드한 이미지를 개발 서버에서 볼 수 있도록 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    