# routine/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from openai import OpenAI
from .models import Exercise, Routine, RoutineExercise
import json
import re
import requests # requests 임포트

# 1. 메인 루틴 선택 페이지
@login_required
def routine_select_view(request):
    """'AI 추천' 또는 '직접 구성'을 선택하는 메인 페이지를 렌더링합니다."""
    context = {'active_menu': 'routine'}
    return render(request, 'routine/routine_select.html', context)

# 2. GPT 기반 추천 루틴 결과 페이지
@login_required
def gpt_plan_view(request):
    """GPT에게 운동 능력에 맞는 상세 루틴(세트, 반복, 무게 포함)을 추천받습니다."""
    level = request.GET.get('level', '초급')
    part = request.GET.get('part', '하체')
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = f"""
    '{part}' 부위를 위한 '{level}' 수준의 웨이트 트레이닝 루틴 5개를 추천해줘.
    각 운동은 반드시 "운동이름::세트::반복횟수::추천무게(kg)" 형식으로 한 줄에 작성해줘.
    예시: 스쿼트::4::12::40
    설명이나 다른 텍스트는 절대 포함하지 말고, 오직 이 형식의 목록만 반환해줘.
    """
    routine_details = []
    try:
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        content = response.choices[0].message.content
        gpt_lines = [line.strip() for line in content.split('\n') if line.strip()]
        for line in gpt_lines:
            parts = line.split('::')
            if len(parts) == 4:
                name, sets, reps, weight = parts
                exercise = Exercise.objects.filter(name__icontains=name.strip()).first()
                if exercise:
                    routine_details.append({
                        'name': exercise.name, 'muscle_group': exercise.muscle_group, 'gif_url': exercise.gif_url,
                        'sets': sets.strip(), 'reps': reps.strip(), 'weight': re.sub(r'[^0-9]', '', weight) or 0,
                        'exercise_type': exercise.exercise_type
                    })
    except Exception as e:
        print(f"GPT Plan View Error: {e}")

    context = {'routine_title': f"AI 추천: {part} ({level}) 루틴", 'routine': routine_details, 'active_menu': 'routine'}
    return render(request, 'routine/routine_plan_with_details.html', context)

# 3. 사용자가 직접 구성한 루틴 생성 및 결과 페이지
@login_required
def custom_plan_view(request):
    """사용자가 직접 입력한 정보로 루틴을 생성하고 저장합니다."""
    exercises_json = request.GET.get('exercises', '[]')
    try:
        exercise_list = json.loads(exercises_json)
    except json.JSONDecodeError:
        return redirect('routine:select')

    if not exercise_list: return redirect('routine:select')
    
    new_routine = Routine.objects.create(user=request.user, name=f"{request.user.username}님의 맞춤 루틴")
    
    routine_details = []
    for item in exercise_list:
        exercise = Exercise.objects.filter(name=item['name']).first()
        if exercise:
            if exercise.exercise_type == 'cardio':
                duration = int(item.get('duration', 0))
                RoutineExercise.objects.create(routine=new_routine, exercise=exercise, duration_minutes=duration)
                routine_details.append({'name': exercise.name, 'muscle_group': exercise.muscle_group, 'gif_url': exercise.gif_url, 'duration': duration, 'exercise_type': 'cardio'})
            else:
                sets_val, reps_val, weight_val = int(item.get('sets', 0)), int(item.get('reps', 0)), int(item.get('weight', 0))
                RoutineExercise.objects.create(routine=new_routine, exercise=exercise, sets=sets_val, reps=reps_val, weight=weight_val)
                routine_details.append({'name': exercise.name, 'muscle_group': exercise.muscle_group, 'gif_url': exercise.gif_url, 'sets': sets_val, 'reps': reps_val, 'weight': weight_val, 'exercise_type': 'strength'})

    context = {'routine_title': "내가 만든 루틴", 'routine': routine_details, 'active_menu': 'routine'}
    return render(request, 'routine/routine_plan_with_details.html', context)

# 4. 내 루틴 목록 페이지
@login_required
def my_routines_view(request):
    """현재 로그인한 사용자가 만든 모든 루틴 목록을 보여줍니다."""
    user_routines = Routine.objects.filter(user=request.user).order_by('-created_at')
    context = {'routines': user_routines, 'active_menu': 'routine_list'}
    return render(request, 'routine/my_routines.html', context)

# 5. 운동 목록 제공 API (수정됨)
def exercise_api(request):
    """특정 근육 그룹에 해당하는 운동 목록을 JSON 형태로 반환합니다."""
    group = request.GET.get('muscle_group')
    if not group:
        return JsonResponse({"error": "muscle_group 파라미터가 필요합니다."}, status=400)

    exercises = Exercise.objects.filter(exercise_type="cardio") if group == "유산소" else Exercise.objects.filter(muscle_group__icontains=group)
    
    # ⭐️ 수정: API 응답에 'exercise_type'을 추가하여 프론트엔드로 전달합니다.
    data = {
        "exercises": [
            {
                "name": ex.name,
                "muscle_group": ex.muscle_group,
                "gif_url": ex.gif_url,
                "exercise_type": ex.exercise_type  # 👈 이 부분이 추가되었습니다!
            }
            for ex in exercises
        ]
    }
    return JsonResponse(data)

# 6. 루틴 삭제 뷰
@require_POST
@login_required
def delete_routine_view(request, routine_id):
    """특정 루틴을 삭제합니다. 현재 로그인한 사용자의 소유인지 반드시 확인합니다."""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    routine.delete()
    return redirect('routine:my_routines')

# 7. 루틴 수정 페이지 뷰 (향후 확장용)
@login_required
def edit_routine_view(request, routine_id):
    """루틴 수정 페이지로 이동합니다. (현재는 목록으로 리다이렉트)"""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    # TODO: 추후에 수정 페이지(routine_edit.html)를 만들어 이곳에서 렌더링
    return redirect('routine:my_routines')

# routine/views.py

# ... 기존의 다른 view들 ...

def youtube_search_api(request):
    """
    쿼리를 받아 YouTube에서 동영상을 검색하고 상위 3개의 결과를 반환하는 API
    """
    query = request.GET.get('q')
    if not query:
        return JsonResponse({'error': '검색어(q)가 필요합니다.'}, status=400)

    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    if not api_key:
        return JsonResponse({'error': 'YouTube API 키가 설정되지 않았습니다.'}, status=500)

    search_url = 'https://www.googleapis.com/youtube/v3/search'
    
    params = {
        'part': 'snippet',
        'q': query,
        'key': api_key,
        'type': 'video',
        'maxResults': 4, # 썸네일 3개만 가져오기
    }

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status() # 오류가 있으면 예외 발생
        results = response.json()
        
        videos = []
        for item in results.get('items', []):
            video_data = {
                'title': item['snippet']['title'],
                'video_id': item['id']['videoId'],
                'thumbnail_url': item['snippet']['thumbnails']['medium']['url'],
            }
            videos.append(video_data)
            
        return JsonResponse({'videos': videos})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': '알 수 없는 오류가 발생했습니다.'}, status=500)