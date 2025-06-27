# achievements/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Achievement, UserAchievement
from accounts.models import Profile
from django.utils.translation import gettext as _

@login_required
def achievements_list(request):
    """
    사용자의 업적 목록과 달성 현황을 보여주는 뷰.
    (최종 수정) 비밀 업적 관련 로직을 완전히 제거하여 단순화합니다.
    """
    
    # ⭐️ FIX: is_secret 필터는 더 이상 필요 없습니다. 모든 업적을 가져옵니다.
    all_achievements = Achievement.objects.order_by('category')
    
    user_achievements = UserAchievement.objects.filter(user=request.user).select_related('achievement')
    user_achievements_dict = {ua.achievement.id: ua for ua in user_achievements}
    achieved_ids = user_achievements_dict.keys()
    
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    # ⭐️ FIX: 이제 비밀 업적을 확인하는 복잡한 if문이 필요 없습니다.
    for ach in all_achievements:
        # 번역 키를 사용하여 번역된 텍스트를 객체의 새 속성으로 추가합니다.
        ach.display_name = _(f"achievement.{ach.codename}.name")
        ach.display_description = _(f"achievement.{ach.codename}.description")
        ach.display_title_reward = _(f"achievement.{ach.codename}.title_reward") if ach.title_reward else ""
    
    # 대표 칭호 번역 처리
    active_title_text = ""
    if profile.active_title:
        active_ach_codename = profile.active_title.achievement.codename
        active_title_text = _(f"achievement.{active_ach_codename}.title_reward")

    context = {
        'all_achievements': all_achievements,
        'user_achievements_dict': user_achievements_dict,
        'achieved_ids': set(achieved_ids),
        'active_title_id': profile.active_title.id if profile.active_title else None,
        'active_title_text': active_title_text,
        'active_menu': 'achievements',
    }
    return render(request, 'achievements/list.html', context)


@login_required
@require_POST
def set_active_title(request, user_achievement_id):
    # 이 함수는 수정할 필요 없습니다.
    user_achievement = get_object_or_404(UserAchievement, id=user_achievement_id, user=request.user)
    if user_achievement.achievement.title_reward:
        profile, created = Profile.objects.get_or_create(user=request.user)
        profile.active_title = user_achievement
        profile.save()
    return redirect('achievements:list')