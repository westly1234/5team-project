# accounts/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from achievements.models import UserAchievement


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics/', default='profile_pics/avatar-default.jpeg')
    height = models.FloatField(null=True, blank=True)
    current_weight = models.FloatField(null=True, blank=True)
    target_weight = models.FloatField(null=True, blank=True)
    skeletal_muscle_mass = models.FloatField(null=True, blank=True)
    body_fat_mass = models.FloatField(null=True, blank=True)
    active_title = models.ForeignKey(
        UserAchievement,
        on_delete=models.SET_NULL, # 칭호의 원본 업적이 삭제되어도 프로필은 유지
        null=True,
        blank=True,
        related_name='activated_by_profile', # 역참조 이름 충돌 방지
        help_text="사용자가 설정한 대표 칭호"
    )
    # ✅ 체지방률 계산 프로퍼티 추가
    @property
    def body_fat_percentage(self):
        # 체중과 체지방량 데이터가 모두 있어야 계산 가능
        if self.current_weight and self.body_fat_mass and self.current_weight > 0:
            # (체지방량 / 현재 체중) * 100
            return (self.body_fat_mass / self.current_weight) * 100
        # 데이터가 없으면 None을 반환
        return None

    def __str__(self):
        return f'{self.user.username} Profile'
    

# ✅ 날짜별 신체 변화를 기록할 새 모델 추가
class BodyCompositionRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='body_records')
    weight = models.FloatField()
    skeletal_muscle_mass = models.FloatField()
    body_fat_mass = models.FloatField()
    # auto_now_add=True : 레코드가 생성될 때의 날짜와 시간이 자동으로 저장됩니다.
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 최신 기록부터 정렬되도록 설정
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"

# User 모델이 생성/저장될 때마다 Profile 모델도 함께 생성/저장되도록 하는 시그널
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    User 객체가 생성되거나 저장될 때 Profile 객체를 확인하고,
    없으면 생성합니다.
    """
    if created:
        # User가 새로 생성되었을 때 Profile 생성
        Profile.objects.create(user=instance)
    else:
        # 기존 User가 업데이트 될 때 (예: 로그인 시 last_login 업데이트)
        # Profile이 있는지 확인하고, 없으면 생성 (이 부분이 핵심!)
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            Profile.objects.create(user=instance)