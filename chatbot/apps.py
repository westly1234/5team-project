# chatbot/apps.py

from django.apps import AppConfig

# 클래스 이름을 ChatbotConfig로 변경
class ChatbotConfig(AppConfig): 
    default_auto_field = 'django.db.models.BigAutoField'
    # name을 'chatbot'으로 변경
    name = 'chatbot' 