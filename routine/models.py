from django.db import models
from django.conf import settings

# ==============================================================================
# 1. Exercise (운동) 모델
# ==============================================================================
# 모든 운동의 '사전' 역할을 하는 모델입니다.
# 관리자가 미리 운동의 이름, 부위, GIF, 타입을 등록해두면,
# 사용자는 이 목록을 보고 자신의 루틴에 추가하게 됩니다.
# ==============================================================================
class Exercise(models.Model):
    # 운동 타입을 '근력'과 '유산소'로 구분하기 위한 선택지
    EXERCISE_TYPES = [
        ('strength', '근력'),
        ('cardio', '유산소'),
    ]

    # 운동 이름 (예: '스쿼트', '러닝머신'). 중복 방지를 위해 unique=True 설정
    name = models.CharField(max_length=100, unique=True, help_text="운동의 고유한 이름")
    
    # 운동 부위 (예: '하체', '가슴', '등')
    muscle_group = models.CharField(max_length=50, blank=True, null=True, help_text="운동이 주로 자극하는 부위")
    
    # 운동 동작을 보여주는 GIF 이미지의 URL
    gif_url = models.URLField(max_length=255, default='https://via.placeholder.com/100x100.png?text=No+Image', help_text="운동 동작 GIF URL")
    
    # 이 운동이 '근력'인지 '유산소'인지 구분하는 타입 필드
    exercise_type = models.CharField(max_length=20, choices=EXERCISE_TYPES, default='strength', help_text="운동의 종류 (근력/유산소)")

    description = models.TextField(
        blank=True, null=True, 
        help_text="운동의 주요 자극 부위 및 방법에 대한 상세 설명"
    )
    precautions = models.TextField(
        blank=True, null=True, 
        help_text="운동 시 주의해야 할 점이나 흔한 실수"
    )

    # 관리자 페이지 등에서 객체를 쉽게 식별하기 위한 문자열 표현
    def __str__(self):
        return f"{self.name} ({self.get_exercise_type_display()})"


# ==============================================================================
# 2. Routine (루틴) 모델
# ==============================================================================
# 사용자가 생성한 하나의 '운동 계획표' 자체를 나타냅니다.
# 이 계획표의 주인은 누구인지, 이름은 무엇인지 등을 저장합니다.
# ==============================================================================
class Routine(models.Model):
    # 이 루틴을 생성한 사용자. 사용자가 삭제되면 관련 루틴도 함께 삭제(CASCADE).
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='routines')
    
    # 루틴의 이름 (예: "user1님의 맞춤 루틴")
    name = models.CharField(max_length=100)
    
    # 이 루틴에 포함된 운동들의 목록.
    # 'through' 옵션을 사용하여 RoutineExercise 모델을 통해 연결됩니다.
    # 이 필드 자체에는 세트, 반복 등의 정보가 저장되지 않습니다.
    exercises = models.ManyToManyField('Exercise', through='RoutineExercise', related_name='exercise_routines')
    
    # 루틴이 생성된 날짜와 시간
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - by {self.user.username}"


# ==============================================================================
# 3. RoutineExercise (루틴-운동 중개) 모델
# ==============================================================================
# Routine과 Exercise의 다대다 관계를 '연결'하며, 그 연결에 대한 '추가 정보'를 저장하는 핵심 모델입니다.
# 예를 들어, "내 가슴 운동 루틴"에 포함된 "벤치프레스"는 "5세트", "10회", "80kg"으로 수행한다는
# 구체적인 정보를 바로 이 모델이 저장합니다.
# ==============================================================================
class RoutineExercise(models.Model):
    # 이 정보가 어떤 루틴에 속해있는지 (FK)
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE)
    
    # 이 정보가 어떤 운동에 대한 것인지 (FK)
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    
    # --- 근력 운동용 필드 ---
    # 유산소 운동일 경우 이 값들은 비어있을(NULL) 수 있습니다.
    sets = models.PositiveIntegerField("세트", null=True, blank=True)
    reps = models.PositiveIntegerField("반복 횟수", null=True, blank=True)
    weight = models.PositiveIntegerField("무게 (kg)", null=True, blank=True)

    # --- 유산소 운동용 필드 ---
    # 근력 운동일 경우 이 값은 비어있을(NULL) 수 있습니다.
    duration_minutes = models.PositiveIntegerField("운동 시간 (분)", null=True, blank=True)
    description = models.TextField(blank=True, null=True, help_text="AI가 생성한 운동 상세 설명")
    precautions = models.TextField(blank=True, null=True, help_text="AI가 생성한 운동 주의사항")
    
    class Meta:
        # 하나의 루틴 안에서 같은 운동이 중복으로 추가되는 것을 방지합니다.
        unique_together = ('routine', 'exercise')
        # 관리자 페이지나 목록에서 최신순으로 정렬하기 위한 기본 설정
        ordering = ['id']

    def __str__(self):
        return f"{self.routine.name}: {self.exercise.name}"