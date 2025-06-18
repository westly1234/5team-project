# chatbot/urls.py

from django.urls import path
# 💥 re_path, serve, static 관련 import는 여기서 필요 없으므로 제거합니다.
#    (TEMP_IMAGE_DIR 서빙은 settings.py에서 다른 방식으로 처리할 것입니다)
from . import views

app_name = 'chatbot' # 👈 URL 패턴의 그룹 이름을 'chatbot'으로 지정

urlpatterns = [
    # API 엔드포인트
    path('api/', views.chatbot_api, name='api'),
    path('new/', views.new_dialog_api, name='new_dialog'),
    path('list/', views.dialog_list_api, name='list'),
    path('load/<int:dialog_id>/', views.load_dialog_api, name='load'),
    path('delete/<int:dialog_id>/', views.delete_dialog_api, name='delete'),
    path('rename/<int:dialog_id>/', views.rename_dialog_api, name='rename'),
    
    # UI 페이지 렌더링 URL (항상 맨 아래에 두는 것이 좋습니다)
    path('', views.chatbot_ui, name='ui'),
]