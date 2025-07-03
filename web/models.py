# web/models.py
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

# ==============================================================
# 모델 1: HealthSurvey (이 부분은 원래 그대로입니다)
# ==============================================================
class HealthSurvey(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="health_survey")
    blood_type = models.CharField(max_length=20)
    allergy = models.JSONField()
    allergy_details = models.TextField(blank=True, null=True)
    chronic_disease = models.JSONField()
    chronic_disease_details = models.TextField(blank=True, null=True)
    surgery_history = models.TextField(blank=True, null=True)
    current_medication = models.TextField(blank=True, null=True)
    supplements = models.TextField(blank=True, null=True)
    smoking_status = models.CharField(max_length=30)
    smoking_period = models.IntegerField(blank=True, null=True)
    smoking_amount = models.IntegerField(blank=True, null=True)
    drinking_frequency = models.CharField(max_length=30)
    drinking_amount = models.CharField(max_length=50, blank=True, null=True)
    family_history = models.JSONField()
    family_history_details = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)


# ==============================================================
# 모델 2: FitnessProfile (이 부분도 원래 그대로입니다)
# ==============================================================
class FitnessProfile(models.Model):
    experience = models.CharField(max_length=10)
    goal = models.CharField(max_length=50)
    goal_text = models.CharField(max_length=100, blank=True, null=True)
    frequency = models.IntegerField()
    weight_unit = models.CharField(max_length=10)
    distance_unit = models.CharField(max_length=10)
    source = models.CharField(max_length=20)
    weight = models.FloatField()
    height = models.FloatField()
    birth = models.DateField()
    gender = models.CharField(max_length=10)
    types = models.CharField(max_length=200)  # 여러 checkbox 값은 view에서 join 처리
    gym = models.CharField(max_length=10)

    def __str__(self):
        # 이 모델에 맞는 __str__ 입니다.
        return f"{self.goal} - {self.gender}"

# ==============================================================
# 모델 3: DailyHealthMetric (✨ 새로 추가하는 모델)
# ==============================================================
class DailyHealthMetric(models.Model):
    """
    사용자의 일별 건강 지표(체중, 골격근량 등) 변화를 기록하는 모델.
    차트 데이터의 원천이 됩니다.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="health_metrics")
    date = models.DateField(db_index=True) # 날짜 (기록일)
    weight = models.FloatField(null=True, blank=True, verbose_name="체중 (kg)")
    skeletal_muscle_mass = models.FloatField(null=True, blank=True, verbose_name="골격근량 (kg)")
    body_fat_mass = models.FloatField(null=True, blank=True, verbose_name="체지방량 (kg)")

    class Meta:
        # 한 명의 사용자는 하루에 하나의 기록만 가질 수 있도록 설정 (중복 방지)
        unique_together = ('user', 'date')
        ordering = ['-date'] # 최신 날짜부터 정렬
        verbose_name = "일별 건강 지표"
        verbose_name_plural = "일별 건강 지표"

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class Inquiry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # 사용자가 탈퇴해도 문의는 남도록 설정
        null=True,
        blank=True,
        verbose_name="문의자 (회원인 경우)"
    )
    CATEGORY_CHOICES = [
        ('account', '계정 관리'),
        ('routine', '운동 루틴'),
        ('diet', '식단'),
        ('feature', '기능 문의'),
        ('bug', '오류/버그 신고'),
        ('etc', '기타'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="문의 유형")
    email = models.EmailField(verbose_name="답변받을 이메일")
    subject = models.CharField(max_length=200, verbose_name="제목")
    message = models.TextField(verbose_name="문의 내용")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="접수 시간")
    is_answered = models.BooleanField(default=False, verbose_name="답변 완료 여부")

    # --- 새로 추가할 부분 ---
    answer = models.TextField(verbose_name="답변 내용", blank=True, null=True)
    answered_at = models.DateTimeField(verbose_name="답변 시간", blank=True, null=True)
    # --- 여기까지 추가 ---

    def __str__(self):
        return f"[{self.get_category_display()}] {self.subject}"

    class Meta:
        verbose_name = "1:1 문의"
        verbose_name_plural = "1:1 문의 목록"
        ordering = ['-created_at']