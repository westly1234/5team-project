from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import now # created_at 기본값 설정을 위해 추가

class ChatConversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    summary_title = models.CharField(max_length=200, default="새 대화") # 기본값 설정
    full_text = models.TextField()  # 전체 대화 저장 (사용자 입력 + 봇 응답 원본 마크다운)
    # summary_text 필드는 현재 views.py에서 직접 사용하고 있지 않으므로, 필요 없다면 제거해도 됩니다.
    # 만약 나중에 요약 기능을 추가할 계획이라면 남겨두세요.
    summary_text = models.TextField(blank=True, null=True)
    
    # 사용자가 직접 제목을 수정했는지 여부를 나타내는 필드
    is_custom_title = models.BooleanField(default=False) 
    
    created_at = models.DateTimeField(default=now, editable=False) # auto_now_add 대신 default=now 사용 고려
    # updated_at = models.DateTimeField(auto_now=True) # 마지막 수정 시간 (선택 사항)

    class Meta:
        ordering = ['-created_at'] # 기본 정렬 순서 (최신 대화가 위로)

    def __str__(self):
        return f"{self.user.username} - {self.summary_title or '제목 없음'}"