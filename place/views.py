# place/views.py

from django.shortcuts import render
from django.conf import settings


def place_search_view(request):
    # context 딕셔너리에 카카오맵 API 키를 담아 템플릿으로 전달합니다.
    context = {
        'kakao_map_api_key': settings.KAKAO_MAP_API_KEY,
        'active_menu': 'place'
    }
    return render(request, 'place/place_search.html', context)