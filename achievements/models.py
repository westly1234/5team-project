# achievements/models.py
from django.db import models
from django.contrib.auth.models import User

class Achievement(models.Model):
    # 업적 카테고리 (필터링에 용이)
    CATEGORY_CHOICES = [
        ('DIET', '식단'),
        ('WORKOUT', '운동'),
        ('CONSISTENCY', '꾸준함'),
        ('EXPLORE', '탐험'),
        ('CHATBOT', '챗봇'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="업적 이름")
    # 업적 달성 시 부여할 칭호 (없는 경우도 있음)
    title_reward = models.CharField(max_length=100, blank=True, null=True, verbose_name="보상 칭호")
    description = models.TextField(verbose_name="업적 설명")
    # 뱃지 이미지 (SVG 또는 PNG)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='WORKOUT', verbose_name="카테고리")
    is_secret = models.BooleanField(default=False, verbose_name="숨겨진 업적 여부")
    # 로직에서 업적을 쉽게 찾기 위한 고유 코드네임
    codename = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="개발용 고유 코드")

    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="사용자")
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, verbose_name="달성한 업적")
    awarded_at = models.DateTimeField(auto_now_add=True, verbose_name="달성 일시")

    class Meta:
        # 한 유저는 같은 업적을 한 번만 달성할 수 있도록 제약
        unique_together = ('user', 'achievement')

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"