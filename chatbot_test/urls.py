from django.urls import path, re_path
from django.conf import settings
from django.views.static import serve
from . import views
from django.conf.urls.static import static

urlpatterns = [
    path('api/', views.chatbot_api, name='chatbot_api'),
    path('new/', views.new_dialog_api, name='new_dialog_api'),
    path('list/', views.dialog_list_api, name='dialog_list_api'),
    path('load/<int:dialog_id>/', views.load_dialog_api, name='load_dialog_api'),
    path('delete/<int:dialog_id>/', views.delete_dialog_api, name='delete_dialog_api'),
    path('rename/<int:dialog_id>/', views.rename_dialog_api, name='rename_dialog_api'),
    re_path(r'^temp_image/(?P<path>.*)$', serve, {
        'document_root': settings.TEMP_IMAGE_DIR,
    }),

    # UI 페이지 렌더링 URL은 맨 마지막에 두는 것이 안전합니다.
    path('', views.chatbot_ui, name='chatbot_ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)