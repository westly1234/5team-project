from django.db import models
from django.contrib.auth.models import User # ✅ 이 줄을 추가하세요!

class Meal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='diet_images/%Y/%m/%d/', blank=True, null=True)
    text_input = models.TextField(blank=True, null=True)
    meal_time = models.CharField(max_length=10, blank=True, null=True)
    analysis_result = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username}의 식단 - {self.created_at.strftime("%Y-%m-%d %H:%M")}'