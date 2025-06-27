# achievements/services.py

from django.contrib import messages
from .models import Achievement, UserAchievement
from django.utils import translation
from django.utils.translation import gettext as _
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

        # ⭐️ 2. 메시지를 생성하기 전에 현재 요청의 언어를 활성화합니다.
        lang_code = translation.get_language_from_request(request)
        with translation.override(lang_code):
            # ⭐️ 3. DB에 저장된 name/description을 번역합니다.
            # (이 부분은 업적 모델의 필드가 name_en, name_es 등으로 되어 있다면 더 나은 방법으로 개선 가능)
            # 현재는 django-modeltranslation 같은 라이브러리를 사용한다고 가정합니다.
            translated_name = achievement.name 

            # ⭐️ 4. 번역된 이름으로 최종 메시지를 생성합니다.
            message_text = _("✨ 업적 달성! [{achievement_name}] 뱃지를 획득했습니다!").format(achievement_name=translated_name)
            messages.success(request, message_text, extra_tags='achievement_unlocked')
            
        return True
    return False