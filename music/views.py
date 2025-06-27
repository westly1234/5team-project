# music/views.py
import json
import logging

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from openai import OpenAI

from achievements.services import check_and_award_achievement
from .models import MusicRecommendationLog, UserMusicPreference

logger = logging.getLogger(__name__)

@login_required
def music_playlist_view(request):
    """음악 추천 페이지를 렌더링합니다."""
    return render(request, 'music/music_playlist.html', {
        'youtube_api_key': settings.YOUTUBE_API_KEY,
        'active_menu': 'music',
    })

@login_required
@require_POST
def get_ai_keywords(request):
    """
    사용자의 선택과 과거 선호도를 바탕으로 AI에게 개인화된 음악 추천 키워드를 요청하고,
    그 과정에서 다양한 업적 달성 여부를 확인합니다.
    """
    try:
        data = json.loads(request.body)
        exercise = data.get('exercise')
        mood = data.get('mood')
        genres = data.get('genres', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

    # 캐시 키 생성 (사용자별, 선택 옵션별로 고유하게)
    cache_key = f"music:keywords:{request.user.id}:{exercise}:{mood}:{'-'.join(sorted(genres))}"
    cached_keywords = cache.get(cache_key)

    if cached_keywords:
        # 업적 처리는 캐시와 무관하게 매번 실행해야 할 수 있으므로, 분리하거나 캐싱 전략을 재고려해야 합니다.
        # 여기서는 편의상 캐시된 결과를 바로 반환합니다.
        return JsonResponse({'keywords': cached_keywords, 'from_cache': True})

    # --- ✨ 개인화 데이터 수집 ✨ ---
    user_prefs = UserMusicPreference.objects.filter(user=request.user)
    # 최근 10개의 '좋아요' 또는 '보관'한 음악 제목
    liked_videos = list(user_prefs.filter(preference_type__in=['liked', 'saved']).order_by('-created_at').values_list('video_title', flat=True)[:10])
    # 최근 10개의 '싫어요'한 음악 제목
    disliked_videos = list(user_prefs.filter(preference_type='disliked').order_by('-created_at').values_list('video_title', flat=True)[:10])

    personalization_prompt_part = ""
    if liked_videos:
        liked_titles = ", ".join(f'"{title}"' for title in liked_videos)
        personalization_prompt_part += f"\n\n### 이 사용자가 과거에 좋아했던 음악 스타일 (이런 종류를 더 많이 추천):\n- {liked_titles}"
    if disliked_videos:
        disliked_titles = ", ".join(f'"{title}"' for title in disliked_videos)
        personalization_prompt_part += f"\n\n### 이 사용자가 싫어했던 음악 스타일 (이런 종류는 제외할 것):\n- {disliked_titles}"

    genre_info = f"선호 장르는 '{genres[0]}'" if genres else "특별히 선호하는 장르는 없음"

    # --- ✨ AI 프롬프트 고도화 ✨ ---
    prompt = f"""
    당신은 사용자의 운동 상황과 기분에 맞는 음악을 추천하는 전문 DJ입니다.
    사용자는 '{exercise}' 운동을 할 예정이며, 현재 기분은 '{mood}'입니다. {genre_info}.
    이 상황에 어울리는 유튜브 '음악 플레이리스트' 또는 '음악 믹스'를 찾을 수 있는 검색 키워드 5개를 추천해주세요.
    인도노래는 배제시켜줘
    **규칙:**
    - 키워드는 실제 유튜브 검색에 사용될 것이므로, 음악 관련 콘텐츠(노래, 연속재생, 믹스, 플레이리스트)가 나올 확률이 높은 구체적인 검색어로 생성해야 합니다.
    - 추천하는 키워드들이 서로 다른 스타일과 아티스트를 포함하도록 다양성을 확보해주세요.
    - 키워드는 한국어 또는 영어로 생성할 수 있습니다.
    - 절대 토크, 강좌, 브이로그, 팟캐스트 관련 키워드를 생성하면 안 됩니다.
    - 출력은 줄바꿈(\n)으로 구분된 키워드 5개만 반환해야 하며, 번호나 설명, 따옴표는 절대 포함하지 마세요.
    {personalization_prompt_part}
    """
  
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 비용 효율적인 최신 모델 사용 권장
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        keywords = [line.strip("12345678910.-• ").strip() for line in content.split('\n') if line.strip()]
        unique_keywords = list(dict.fromkeys(keywords)) # 중복 제거

        if not unique_keywords:
            raise ValueError("AI가 유효한 키워드를 생성하지 못했습니다.")

        # 성공 시 캐시에 저장 (유효 시간: 1시간)
        cache.set(cache_key, unique_keywords, timeout=3600)

    except Exception as e:
        logger.error(f"OpenAI API 호출 오류: {e}")
        return JsonResponse({'error': 'AI 응답 생성에 실패했습니다. 잠시 후 다시 시도해주세요.'}, status=500)
    
    # --- ✨ 업적 달성 확인 로직 (AI 호출 성공 후 실행) ✨ ---
    try:
        # 1. 추천 요청 로그 저장
        MusicRecommendationLog.objects.create(user=request.user, exercise=exercise, mood=mood)

        # 2. 첫 사용 업적
        check_and_award_achievement(request, request.user, 'ai_music_buddy')

        # 3. 누적 사용 횟수 업적
        log_count = MusicRecommendationLog.objects.filter(user=request.user).count()
        if log_count >= 5: check_and_award_achievement(request, request.user, 'music_curator_bronze')
        if log_count >= 20: check_and_award_achievement(request, request.user, 'music_curator_silver')
        if log_count >= 50: check_and_award_achievement(request, request.user, 'music_curator_gold')
        if log_count >= 100: check_and_award_achievement(request, request.user, 'music_curator_platinum')

        # 4. 탐험 업적
        logs = MusicRecommendationLog.objects.filter(user=request.user)
        if logs.values_list('mood', flat=True).distinct().count() >= 4:
            check_and_award_achievement(request, request.user, 'mood_maker')
        if logs.values_list('exercise', flat=True).distinct().count() >= 4: # 템플릿 운동 옵션 4개
            check_and_award_achievement(request, request.user, 'versatile_exerciser')

        # 5. 특정 조합 업적
        if '요가' in exercise and '차분하게' in mood:
            check_and_award_achievement(request, request.user, 'meditation_time')
        if 'hiit' in exercise.lower() and '에너지' in mood:
            check_and_award_achievement(request, request.user, 'heart_beater')
            
    except Exception as e:
        logger.exception("업적 처리 중 오류 발생")

    return JsonResponse({'keywords': unique_keywords, 'from_cache': False})


@login_required
@require_POST
def handle_music_preference(request):
    """사용자의 음악 선호도(보관/취소)를 처리하고 업적을 확인합니다."""
    try:
        data = json.loads(request.body)
        video_id = data.get('videoId')
        video_title = data.get('videoTitle')
        action = data.get('action') # 'save' 또는 'unsave'

        if not all([video_id, video_title, action]):
            return JsonResponse({'error': '필수 데이터가 누락되었습니다.'}, status=400)

        if action == 'save':
            # 기존 기록이 있으면 업데이트, 없으면 생성
            obj, created = UserMusicPreference.objects.update_or_create(
                user=request.user,
                video_id=video_id,
                preference_type='saved', # 'saved' 타입으로 고정
                defaults={'video_title': video_title}
            )
            message = f'"{video_title}"이(가) 보관함에 추가되었습니다.'
            
            # '내 보관함 지킴이' 업적: 첫 음악 보관 시
            if created:
                 check_and_award_achievement(request, request.user, 'my_playlist_guard')

        elif action == 'unsave':
            # 해당 조건의 기록을 찾아서 삭제
            deleted_count, _ = UserMusicPreference.objects.filter(
                user=request.user,
                video_id=video_id,
                preference_type='saved'
            ).delete()
            
            if deleted_count > 0:
                message = f'"{video_title}"이(가) 보관함에서 삭제되었습니다.'
            else:
                message = '삭제할 항목을 찾지 못했습니다.' # 이미 삭제된 경우

        else:
            return JsonResponse({'error': '알 수 없는 액션입니다.'}, status=400)

        return JsonResponse({'status': 'success', 'message': message})

    except Exception as e:
        logger.error(f"음악 선호도 처리 중 오류: {e}")
        return JsonResponse({'error': '요청 처리 중 오류가 발생했습니다.'}, status=500)