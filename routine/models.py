from django.db import models
from django.conf import settings
from django.utils import timezone

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
    gif_url = models.URLField(max_length=255, default='https://via.placeholder.com/100x100.png?text=No+Image', help_text="운동 동작 GIF URL")
    exercise_type = models.CharField(max_length=20, choices=EXERCISE_TYPES, default='strength', help_text="운동의 종류 (근력/유산소)")
    description = models.TextField(blank=True, null=True, help_text="운동의 주요 자극 부위 및 방법에 대한 상세 설명")
    precautions = models.TextField(blank=True, null=True, help_text="운동 시 주의해야 할 점이나 흔한 실수")

    def __str__(self):
        return f"{self.name} ({self.get_exercise_type_display()})"

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
