# achievements/services.py

from django.contrib import messages
from .models import Achievement, UserAchievement
import logging

logger = logging.getLogger(__name__)

def check_and_award_achievement(request, user, codename):
    try:
        achievement = Achievement.objects.get(codename=codename)
    except Achievement.DoesNotExist:
        logger.warning(f"업적을 찾을 수 없습니다: codename='{codename}'이 DB에 존재하지 않습니다.")
        return False

    if not UserAchievement.objects.filter(user=user, achievement=achievement).exists():
        UserAchievement.objects.create(user=user, achievement=achievement)

        # ✅ 1. JSON 파일에 있는 업적 이름의 '번역 키'를 만듭니다.
        #    예: "achievement.workout_log_365.name"
        achievement_name_key = f"achievement.{achievement.codename}.name"
        
        # ✅ 2. 다른 어떤 문자열도 섞지 말고, 이 '번역 키' 자체를 메시지로 저장합니다.
        messages.success(request, achievement_name_key, extra_tags='achievement_unlocked')
            
        return True
    return False