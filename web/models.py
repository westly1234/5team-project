from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

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
        return f"{self.goal} - {self.gender}"

