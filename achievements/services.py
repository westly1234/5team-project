# achievements/services.py

from django.contrib import messages
from .models import Achievement, UserAchievement
import logging
from web.utils import t # ✨ 1. t 함수를 임포트합니다.
from django.utils import translation

logger = logging.getLogger(__name__)

def check_and_award_achievement(request, user, codename, extra_tags=''):
    try:
        achievement = Achievement.objects.get(codename=codename)
    except Achievement.DoesNotExist:
        logger.warning(f"업적을 찾을 수 없습니다: codename='{codename}'이 DB에 존재하지 않습니다.")
        return False

    if not UserAchievement.objects.filter(user=user, achievement=achievement).exists():
        UserAchievement.objects.create(user=user, achievement=achievement)

        lang_code = translation.get_language_from_request(request)
        achievement_name_key = f"achievement.{achievement.codename}.name"
        translated_message = t(achievement_name_key, lang_code=lang_code)
        final_tags = f'achievement_unlocked {extra_tags}'.strip()
        messages.success(request, translated_message, extra_tags=final_tags)

        return True
    return False