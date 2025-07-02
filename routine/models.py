from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils import translation # ✅ 현재 언어를 가져오기 위해 import

class Exercise(models.Model):
    EXERCISE_TYPES = [
        ('strength', '근력'),
        ('cardio', '유산소'),
    ]

    name = models.CharField(max_length=100, unique=True, help_text="운동의 고유한 이름")
    name_en = models.CharField(max_length=100, blank=True, null=True, help_text="운동 이름 (영어)")
    name_es = models.CharField(max_length=100, blank=True, null=True, help_text="운동 이름 (스페인어)")
    muscle_group = models.CharField(max_length=50, blank=True, null=True, help_text="운동이 주로 자극하는 부위")
    muscle_group_en = models.CharField(max_length=50, blank=True, null=True, help_text="운동 부위 (영어)")
    muscle_group_es = models.CharField(max_length=50, blank=True, null=True, help_text="운동 부위 (스페인어)")
    gif_url = models.ImageField(upload_to='exercise_gifs/', blank=True, null=True)
    exercise_type = models.CharField(max_length=20, choices=EXERCISE_TYPES, default='strength', help_text="운동의 종류 (근력/유산소)")
    description = models.TextField(blank=True, null=True, help_text="운동의 주요 자극 부위 및 방법에 대한 상세 설명")
    precautions = models.TextField(blank=True, null=True, help_text="운동 시 주의해야 할 점이나 흔한 실수")
    description_en = models.TextField(blank=True, null=True, help_text="운동 설명 (영어)")
    precautions_en = models.TextField(blank=True, null=True, help_text="운동 주의사항 (영어)")
    description_es = models.TextField(blank=True, null=True, help_text="운동 설명 (스페인어)")
    precautions_es = models.TextField(blank=True, null=True, help_text="운동 주의사항 (스페인어)")

    # ✅ 아래 localized 프로퍼티들이 추가되었습니다.
    # 이 프로퍼티들은 뷰나 템플릿에서 exercise.localized_name처럼 호출하면
    # 현재 설정된 언어에 맞는 값을 자동으로 반환해줍니다.
    @property
    def get_final_gif_url(self):
        """
        gif_url 필드가 내부 파일인지 외부 URL인지 확인하여
        항상 올바른 최종 URL을 반환하는 프로퍼티.
        """
        if not self.gif_url:
            return ""  # 값이 없으면 빈 문자열 반환

        # ImageField에 저장된 값의 실제 타입을 확인
        # DB에 저장된 값이 http로 시작하는 '문자열'인 경우, 
        # Django는 이를 ImageFieldFile 객체로 감싸지만, name 속성은 원본 문자열을 가짐
        if hasattr(self.gif_url, 'name') and self.gif_url.name.startswith(('http://', 'https://')):
            # 외부 URL인 경우, 해당 URL 문자열 자체를 반환
            return self.gif_url.name
        
        # 그 외의 경우 (정상적인 내부 파일 경로인 경우)
        if hasattr(self.gif_url, 'url'):
            try:
                # .url 속성을 통해 '/media/...' 경로를 생성하여 반환
                return self.gif_url.url
            except ValueError:
                # 파일이 없는 ImageFieldFile 객체 등 예외 처리
                return ""
        
        # 혹시 모를 다른 경우 (예: 순수 문자열 필드였다가 ImageField로 바뀐 경우)
        return ""
        
    @property
    def localized_name(self):
        """현재 언어 설정에 맞는 운동 이름을 반환합니다."""
        lang = translation.get_language()  # 현재 활성화된 언어 코드 (예: 'ko', 'en')
        if lang == 'en' and self.name_en:
            return self.name_en
        if lang == 'es' and self.name_es:
            return self.name_es
        return self.name  # 기본값 또는 해당하는 언어 필드가 없을 경우 한국어 이름 반환

    @property
    def localized_muscle_group(self):
        """현재 언어 설정에 맞는 운동 부위를 반환합니다."""
        lang = translation.get_language()
        if lang == 'en' and self.muscle_group_en:
            return self.muscle_group_en
        if lang == 'es' and self.muscle_group_es:
            return self.muscle_group_es
        return self.muscle_group

    @property
    def localized_description(self):
        """현재 언어 설정에 맞는 운동 설명을 반환합니다."""
        lang = translation.get_language()
        if lang == 'en' and self.description_en:
            return self.description_en
        if lang == 'es' and self.description_es:
            return self.description_es
        return self.description

    @property
    def localized_precautions(self):
        """현재 언어 설정에 맞는 운동 주의사항을 반환합니다."""
        lang = translation.get_language()
        if lang == 'en' and self.precautions_en:
            return self.precautions_en
        if lang == 'es' and self.precautions_es:
            return self.precautions_es
        return self.precautions

    def __str__(self):
        # 관리자 페이지 등에서 보기 편하도록 영문 이름을 함께 표시
        return f"{self.name} ({self.name_en or 'No English Name'})"


class Routine(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='routines')
    name = models.CharField(max_length=100)
    exercises = models.ManyToManyField('Exercise', through='RoutineExercise', related_name='exercise_routines')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - by {self.user.username}"


class RoutineExercise(models.Model):
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    sets = models.PositiveIntegerField("세트", null=True, blank=True)
    reps = models.PositiveIntegerField("반복 횟수", null=True, blank=True)
    weight = models.PositiveIntegerField("무게 (kg)", null=True, blank=True)
    duration_minutes = models.PositiveIntegerField("운동 시간 (분)", null=True, blank=True)
    description = models.TextField(blank=True, null=True, help_text="AI가 생성한 운동 상세 설명")
    precautions = models.TextField(blank=True, null=True, help_text="AI가 생성한 운동 주의사항")

    class Meta: 
        unique_together = ('routine', 'exercise')
        ordering = ['id']

    def __str__(self):
        return f"{self.routine.name}: {self.exercise.name}"


class WorkoutLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_logs')
    routine = models.ForeignKey(Routine, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    completed_at = models.DateTimeField(default=timezone.now)
    total_duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="실제 총 운동 시간(분)")
    memo = models.TextField(blank=True, null=True, help_text="오늘 운동 어땠나요?")

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.username} - {self.completed_at.strftime('%Y-%m-%d %H:%M')} 운동 완료"