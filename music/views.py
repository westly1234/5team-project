# music/views.py

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import logging
from openai import OpenAI
from django.contrib.auth.decorators import login_required

# ✅ 업적 및 모델 임포트
from achievements.services import check_and_award_achievement
from .models import MusicRecommendationLog

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
    사용자의 운동 종류와 기분을 받아 AI에게 음악 추천 키워드를 요청하고,
    그 과정에서 다양한 업적 달성 여부를 확인합니다.
    """

    data = json.loads(request.body)
    exercise = data.get('exercise')
    mood = data.get('mood')

    # AI에게 키워드 추천을 요청하는 프롬프트
    prompt = f"""
    '{exercise}' 운동을 할 때 '{mood}' 기분에 잘 어울리는 유튜브 내 '음악 전용 플레이리스트'나 '음악 믹스 영상' 키워드를 12개 추천해줘.

    - 각 키워드는 실제 유튜브에서 검색했을 때 음악 콘텐츠(노래, 연속재생, 믹스, 플레이리스트)만 뜨도록 구성해줘.
    - 의미 없는 단어 없이 명확한 검색어만 추천해줘.
    - 음악 외 콘텐츠(토크, 브이로그 등)가 포함되지 않도록 주의해줘.
    - 출력되는 영상이 중복되는 것이 없게끔 해줘
    - 출력은 줄바꿈(\n)으로 구분된 키워드 12개만 반환해줘. 설명은 포함하지 마.
    """
  
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        keywords = [line.strip("12345678910.-• ").strip() for line in content.split('\n') if line.strip()]
        unique_keywords = list(dict.fromkeys(keywords))
    except Exception as e:
        return JsonResponse({'error': 'AI 응답에 실패했습니다.'}, status=500)
        # --- ✨ 업적 달성 확인 로직 시작 ✨ ---
    try:
        # 1. 추천 요청 로그 저장
        MusicRecommendationLog.objects.create(
            user=request.user, 
            exercise=exercise, 
            mood=mood
        )

        # 2. 첫 사용 업적
        check_and_award_achievement(request, request.user, 'ai_music_buddy')

        # 3. 누적 사용 횟수 업적
        log_count = MusicRecommendationLog.objects.filter(user=request.user).count()
        if log_count >= 5:
            check_and_award_achievement(request, request.user, 'music_curator_bronze')
        if log_count >= 20:
            check_and_award_achievement(request, request.user, 'music_curator_silver')
        if log_count >= 50:
            check_and_award_achievement(request, request.user, 'music_curator_gold')
        if log_count >= 100:
            check_and_award_achievement(request, request.user, 'music_curator_platinum')

        # 4. 탐험 업적
        logs = MusicRecommendationLog.objects.filter(user=request.user)

        unique_moods_count = logs.values_list('mood', flat=True).distinct().count()
        if unique_moods_count >= 4: # 템플릿에 기분 옵션이 4개이므로
            check_and_award_achievement(request, request.user, 'mood_maker')

        unique_exercises_count = logs.values_list('exercise', flat=True).distinct().count()
        if unique_exercises_count >= 5: # 템플릿에 운동 옵션이 5개
            check_and_award_achievement(request, request.user, 'versatile_exerciser')

        # 5. 특정 조합 업적
        current_exercise_lower = exercise.lower()
        current_mood_lower = mood.lower()

        # '명상의 시간' 업적: '요가/필라테스' + '편안하고 차분하게' 조합
        if '요가' in current_exercise_lower and '차분하게' in current_mood_lower:
            check_and_award_achievement(request, request.user, 'meditation_time')

        # '심장을 울려라' 업적: 'HIIT' + '에너지 넘치게' 조합
        if 'hiit' in current_exercise_lower and '에너지' in current_mood_lower:
            check_and_award_achievement(request, request.user, 'heart_beater')
            
        # --- ✨ 업적 달성 확인 로직 끝 ✨ ---

    except Exception as e:
        # 로깅은 하되, 사용자에겐 영향 없음
        logger.exception("업적 처리 중 오류 발생")

    return JsonResponse({'keywords': unique_keywords})