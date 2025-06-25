# music/models.py
from django.db import models
from django.conf import settings

class MusicRecommendationLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    exercise = models.CharField(max_length=100)
    mood = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.exercise} ({self.mood})"

class UserMusicPreference(models.Model):
    """사용자의 음악 선호도를 기록하는 모델"""
    class PreferenceType(models.TextChoices):
        LIKED = 'liked', '좋아요'
        DISLIKED = 'disliked', '싫어요'
        SAVED = 'saved', '보관'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    video_id = models.CharField(max_length=50, help_text="YouTube Video ID")
    video_title = models.CharField(max_length=255)
    preference_type = models.CharField(max_length=10, choices=PreferenceType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 한 사용자가 같은 영상에 대해 같은 타입의 피드백을 중복으로 남기지 않도록 설정
        unique_together = ('user', 'video_id', 'preference_type') 

    def __str__(self):
        return f"{self.user.username} - {self.video_title} ({self.get_preference_type_display()})"