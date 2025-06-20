# place/models.py
from django.db import models
from django.conf import settings

class PlaceSearchLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.CharField(max_length=100, help_text="검색한 장소 카테고리 (예: 헬스장)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - '{self.category}' 검색 ({self.created_at.strftime('%Y-%m-%d')})"