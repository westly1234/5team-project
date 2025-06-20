# achievements/services.py
from django.contrib import messages
from .models import Achievement, UserAchievement

def check_and_award_achievement(request, user, codename):
    """
    주어진 코드네임에 해당하는 업적을 유저가 달성했는지 확인하고,
    조건 충족 시 업적을 부여하며, 알림 메시지를 생성합니다.
    """
    try:
        # 1. 달성하려는 업적 가져오기
        achievement = Achievement.objects.get(codename=codename)

        # 2. 이미 달성했는지 확인 (중복 방지)
        if UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            return # 이미 달성했으면 아무것도 안 함

        # 3. 업적 달성 조건 확인 (여기가 핵심!)
        #    각 업적의 고유한 달성 조건을 여기에 구현합니다.
        #    예를 들어, '누적 10회 식단 기록'이라면 식단 기록 수를 세는 로직이 필요합니다.
        #    단순 1회성 업적은 별도 조건 없이 바로 부여 가능합니다.
        
        # (예시) 'first_meal_record'의 경우, 이 함수가 호출되었다는 것 자체가
        # 식단을 기록했다는 의미이므로 별도 조건 없이 통과시킵니다.
        # 복잡한 조건은 여기서 분기 처리합니다.
        
        # 4. 업적 부여 및 알림
        UserAchievement.objects.create(user=user, achievement=achievement)
        messages.success(request, f"✨ 업적 달성! [{achievement.name}] 뱃지를 획득했습니다!")

    except Achievement.DoesNotExist:
        # 코드네임에 해당하는 업적이 DB에 없는 경우
        pass