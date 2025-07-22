from django.contrib import admin
from django.urls import path, include
from web import views as web_views  # home 뷰를 위해 필요
from django.conf import settings
from django.conf.urls.static import static
from accounts import views as accounts_views  # save_survey_view를 위해 필요c

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path("accounts/", include("accounts.urls")),
    path('save-survey/', accounts_views.save_survey_view, name='save_survey_ajax'),
    path('services/', web_views.services_page, name='services_page'),
    path('web/', include(('web.urls', 'web'), namespace='web')),
    path('music/', include('music.urls')), 
    path('place/', include('place.urls')),
    path('routine/', include('routine.urls')),
    path('diet/', include('diet.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('achievements/', include('achievements.urls')),
    path('store/', include('store.urls')),

    # 홈페이지 (http://127.0.0.1:8000/)는 여기서 직접 처리
    path('', web_views.home, name='home'),
]

# 미디어 파일 설정을 위한 부분
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)