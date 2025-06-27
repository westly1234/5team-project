# achievements/models.py
from django.db import models
from django.conf import settings # ⭐️ User 모델은 settings에서 가져오는 것이 좋습니다.
from django.utils.translation import gettext_lazy as _ # ⭐️ 번역 함수 import

class Achievement(models.Model):
    # ⭐️ 카테고리 선택지를 _()로 감쌉니다.
    CATEGORY_CHOICES = [
        ('DIET', _('식단')),
        ('WORKOUT', _('운동')),
        ('CONSISTENCY', _('꾸준함')),
        ('EXPLORE', _('탐험')),
        ('CHATBOT', _('챗봇')),
    ]

    # --- 원본 필드 (번역 대상 아님) ---
    codename = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text=_("개발용 고유 코드"))
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='WORKOUT')
    is_secret = models.BooleanField(default=False)

    # --- ⭐️ 번역이 필요한 필드들 ⭐️ ---
    name = models.CharField(max_length=100, unique=True)
    title_reward = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    
    name_en = models.CharField(max_length=100, blank=True, null=True)
    title_reward_en = models.CharField(max_length=100, blank=True, null=True)
    description_en = models.TextField(blank=True, null=True)

    name_es = models.CharField(max_length=100, blank=True, null=True)
    title_reward_es = models.CharField(max_length=100, blank=True, null=True)
    description_es = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("업적")
        verbose_name_plural = _("업적 목록")

class UserAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("사용자"))
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, verbose_name=_("달성한 업적"))
    awarded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("달성 일시"))

    class Meta:
        unique_together = ('user', 'achievement')
        verbose_name = _("사용자 달성 업적")
        verbose_name_plural = _("사용자 달성 업적 목록")

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"