# chatbot_test/models.py

from django.db import models
from django.conf import settings
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

class ChatConversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("사용자"))
    
    summary_title = models.CharField(max_length=200, null=True, blank=True, verbose_name=_("대화 제목"))

    full_text = models.TextField(verbose_name=_("전체 대화 내용"))
    summary_text = models.TextField(blank=True, null=True, verbose_name=_("요약 내용"))
    is_custom_title = models.BooleanField(default=False, verbose_name=_("사용자 지정 제목 여부"))
    created_at = models.DateTimeField(default=now, editable=False, verbose_name=_("생성일"))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _("챗봇 대화")
        verbose_name_plural = _("챗봇 대화 목록")

    def __str__(self):
        if self.summary_title:
            # format을 사용하기 전에 번역합니다.
            return f"{self.user.username} - {self.summary_title}"
        else:
            # 제목이 없을 경우, 번역된 '제목 없음'을 보여줍니다.
            return f"{self.user.username} - {_('제목 없음')}"

class ChatbotInteractionLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} at {self.created_at}"