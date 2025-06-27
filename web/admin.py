from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import HealthSurvey, FitnessProfile
from django.core.mail import send_mail
from django.utils import timezone
from .models import Inquiry
from django.template.loader import render_to_string
from django.conf import settings

User = get_user_model()

# HealthSurvey를 사용자 상세 페이지에서 inline으로 보여주기 위한 설정
class HealthSurveyInline(admin.StackedInline):
    model = HealthSurvey
    can_delete = False
    verbose_name_plural = 'Health Survey'

# 기존 UserAdmin에 inline 추가
class CustomUserAdmin(BaseUserAdmin):
    inlines = (HealthSurveyInline,)

# 기존 UserAdmin 등록 해제 후, 커스텀으로 재등록
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# 기타 모델들은 일반 방식으로 등록
admin.site.register(FitnessProfile)

@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    # --- 이 부분은 기존 코드와 100% 동일합니다 ---
    list_display = ('user', 'subject', 'email', 'is_answered', 'created_at')
    list_filter = ('is_answered', 'category', 'created_at')
    search_fields = ('user__username', 'subject', 'email', 'message')
    fieldsets = (
        ('문의 정보', {'fields': ('user', 'category', 'subject', 'email', 'created_at')}),
        ('문의 내용', {'fields': ('message',)}),
        ('답변 관리', {'fields': ('answer', 'is_answered', 'answered_at')}),
    )
    readonly_fields = ('user', 'created_at', 'answered_at')
    actions = ['send_answer_email']
    # --- 여기까지 기존 코드와 동일 ---

    # ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ 이 함수만 바뀝니다 ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
    @admin.action(description="선택된 문의에 답변 메일 발송 및 완료 처리")
    def send_answer_email(self, request, queryset):
        """
        선택된 문의에 답변을 이메일로 발송하고, '답변 완료'로 상태를 변경합니다.
        (HTML 템플릿을 사용하도록 수정됨)
        """
        success_count = 0
        fail_count = 0
        
        for inquiry in queryset:
            # 기존 코드와 동일: 답변 내용이 없으면 건너뜁니다.
            if not inquiry.answer:
                self.message_user(request, f"'{inquiry.subject}' 문의에 답변이 작성되지 않아 메일을 보낼 수 없습니다.", level=messages.ERROR)
                fail_count += 1
                continue

            # 이메일 발송 로직
            try:
                # [수정] 템플릿에 보낼 데이터 준비
                context = {
                    'user_name': inquiry.user.username if inquiry.user else '고객',
                    'admin_reply': inquiry.answer,
                }
                
                # [수정] 'reply_email.html' 템플릿으로 HTML 이메일 본문 생성
                html_message = render_to_string('web/reply_email.html', context)

                # [수정] HTML 형식으로 이메일 발송
                send_mail(
                    subject=f"[HealthWise] '{inquiry.subject}' 문의에 대한 답변입니다.",
                    message='',  # 일반 텍스트는 비워둠
                    from_email=settings.DEFAULT_FROM_EMAIL, # settings.py의 기본 발신자 사용
                    recipient_list=[inquiry.email],
                    fail_silently=False,
                    html_message=html_message # HTML 본문 전달
                )
                
                # 기존 코드와 동일: 상태 업데이트
                inquiry.is_answered = True
                inquiry.answered_at = timezone.now()
                inquiry.save()
                
                success_count += 1

            except Exception as e:
                # 기존 코드와 동일: 에러 처리
                self.message_user(request, f"'{inquiry.subject}' 메일 발송 중 오류: {e}", level=messages.ERROR)
                fail_count += 1
        
        # 기존 코드와 동일: 최종 결과 메시지
        if success_count > 0:
            self.message_user(request, f"{success_count}개의 문의에 대한 답변을 성공적으로 발송했습니다.", level=messages.SUCCESS)
        if fail_count > 0:
            self.message_user(request, f"{fail_count}개의 문의 답변 발송에 실패했습니다.", level=messages.WARNING)
