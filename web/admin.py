from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import HealthSurvey, FitnessProfile

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
