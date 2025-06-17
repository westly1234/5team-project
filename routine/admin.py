# routine/admin.py

from django.contrib import admin
from .models import Exercise, Routine # 같은 폴더의 models.py에서 모델들을 가져옵니다.

# 1. Exercise 모델을 관리자 페이지에 등록합니다.
@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    # 목록에 보여줄 항목들
    list_display = ('name', 'muscle_group', 'exercise_type')
    # 필터링 옵션
    list_filter = ('muscle_group', 'exercise_type')
    # 검색 기능
    search_fields = ('name',)

# 2. Routine 모델도 관리자 페이지에 등록합니다.
# (이 모델은 사용자가 직접 추가하는 것이 아니므로 간단하게 등록만 합니다.)
admin.site.register(Routine)