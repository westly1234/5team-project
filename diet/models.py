# diet/models.py

from django.db import models
from django.conf import settings

class Meal(models.Model):
    # 사용자와 1:N 관계
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # 입력 데이터
    image = models.ImageField(upload_to='diet_images/%Y/%m/%d/', blank=True, null=True, help_text="사용자가 업로드한 음식 사진")
    text_input = models.TextField(blank=True, help_text="사용자가 글로 입력한 음식 내용 (예: 사과 1개, 닭가슴살 샐러드)")
    
    # 분석 결과
    analysis_result = models.JSONField(blank=True, null=True, help_text="OpenAI API의 분석 결과(JSON)를 저장")
    
    # 생성 시각
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}의 {self.created_at.strftime('%Y-%m-%d')} 식단"