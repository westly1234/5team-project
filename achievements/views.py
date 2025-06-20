# achievements/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Achievement, UserAchievement
from accounts.models import Profile # Profile 모델 import

@login_required
def achievements_list(request):
    all_achievements = Achievement.objects.order_by('category')
    user_achievements = UserAchievement.objects.filter(user=request.user).select_related('achievement')
    user_achievements_dict = {ua.achievement.id: ua for ua in user_achievements}
    achieved_ids = user_achievements_dict.keys()
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    context = {
        'all_achievements': all_achievements,
        'user_achievements_dict': user_achievements_dict,
        'achieved_ids': set(achieved_ids),
        'active_title': profile.active_title,
        'active_menu': 'achievements',  # ✅ 이 부분을 추가해주세요!
    }
    return render(request, 'achievements/list.html', context)


@login_required
@require_POST # POST 요청만 허용
def set_active_title(request, user_achievement_id):
    # 1. 내가 달성한 업적이 맞는지 확인
    user_achievement = get_object_or_404(
        UserAchievement, 
        id=user_achievement_id, 
        user=request.user
    )

    # 2. 해당 업적이 칭호를 부여하는지 확인
    if user_achievement.achievement.title_reward:
        profile = Profile.objects.get(user=request.user)
        profile.active_title = user_achievement
        profile.save()
    
    # 3. 업적 목록 페이지로 리다이렉트
    return redirect('achievements:list')