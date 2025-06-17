# music/views.py

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from openai import OpenAI

def music_playlist_view(request):
    return render(request, 'music/music_playlist.html', {
        'youtube_api_key': settings.YOUTUBE_API_KEY,
        'active_menu': 'music',
    })

@require_POST
def get_ai_keywords(request):
    data = json.loads(request.body)
    exercise = data.get('exercise')
    mood = data.get('mood')

    # ✅ [수정됨] AI에게 10개의 키워드를 요청하도록 프롬프트 변경
    prompt = f"""
    {exercise} 운동을 할 때 '{mood}' 기분에 잘 어울리는 유튜브 내 '음악 전용 플레이리스트'나 '음악 믹스 영상' 키워드를 12개 추천해줘.

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
        
        # ✅ [수정됨] 생성된 키워드 리스트에서 중복을 제거
        unique_keywords = list(dict.fromkeys(keywords))
        
        return JsonResponse({'keywords': unique_keywords})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)