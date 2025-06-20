# place/views.py

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.utils import timezone
from django.contrib.auth.decorators import login_required

# ✅ 업적 및 모델 임포트
from achievements.services import check_and_award_achievement
from .models import PlaceSearchLog

@login_required
def place_search_view(request):
    """장소 검색 페이지를 렌더링합니다."""
    context = {
        'kakao_map_api_key': settings.KAKAO_MAP_API_KEY,
        'active_menu': 'place'
    }
    return render(request, 'place/place_search.html', context)

@login_required
@require_POST
def log_place_search_api(request):
    """
    사용자의 장소 검색 활동을 기록하고,
    관련 업적 달성 여부를 확인하는 API 뷰입니다.
    """
    try:
        data = json.loads(request.body)
        category = data.get('category')

        if not category:
            return JsonResponse({'error': '검색 카테고리가 필요합니다.'}, status=400)

        # --- ✨ 업적 달성 확인 로직 시작 ✨ ---
        user = request.user

        # 1. 검색 로그 저장
        PlaceSearchLog.objects.create(user=user, category=category)

        # 2. 첫 사용 업적
        check_and_award_achievement(request, user, 'place_explorer_basic') # '지역 탐험가'

        # 3. 누적 사용 횟수 업적
        log_count = PlaceSearchLog.objects.filter(user=user).count()
        if log_count >= 5:
            check_and_award_achievement(request, user, 'place_search_bronze') # '동네 전문가'
        if log_count >= 20:
            check_and_award_achievement(request, user, 'place_search_silver') # '도시 탐험가'
        if log_count >= 50:
            check_and_award_achievement(request, user, 'place_search_gold') # 'GPS 마스터'

        # 4. 탐험 업적 (다양한 카테고리 검색)
        logs = PlaceSearchLog.objects.filter(user=user)
        unique_categories_count = logs.values_list('category', flat=True).distinct().count()
        if unique_categories_count >= 3:
            check_and_award_achievement(request, user, 'sports_maniac') # '스포츠 매니아'
        if unique_categories_count >= 6: # 제공된 카테고리 6개 모두 검색 시
            check_and_award_achievement(request, user, 'grand_slammer') # '그랜드 슬래머'

        # 5. 특정 카테고리 검색 업적
        category_lower = category.lower()
        if '헬스장' in category_lower:
            check_and_award_achievement(request, user, 'iron_path_search') # '강철의 길'
        if '요가' in category_lower:
            check_and_award_achievement(request, user, 'inner_peace_search') # '내면의 평화'
        if '수영장' in category_lower:
            check_and_award_achievement(request, user, 'aqua_adventurer_search') # '아쿠아 어드벤처'
        if any(sport in category_lower for sport in ['테니스', '축구', '탁구']):
            check_and_award_achievement(request, user, 'ball_is_life_search') # '공은 나의 친구'

        # 6. 히든 업적 (시간 기반)
        now = timezone.now()
        if now.hour >= 22 or now.hour < 4: # 밤 10시 ~ 새벽 4시
            check_and_award_achievement(request, user, 'night_planner') # '밤의 계획가'
        if now.weekday() >= 5: # 토요일(5), 일요일(6)
            check_and_award_achievement(request, user, 'weekend_warrior_search') # '주말의 전사'

        # --- ✨ 업적 달성 확인 로직 끝 ✨ ---

        return JsonResponse({'success': True, 'message': '검색 활동이 기록되었습니다.'})

    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'서버 오류가 발생했습니다: {str(e)}'}, status=500)