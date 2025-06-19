# routine/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from openai import OpenAI
from .models import Exercise, Routine, RoutineExercise
import json
import re
import requests

# 1. 메인 루틴 선택 페이지
@login_required
def routine_select_view(request):
    context = {'active_menu': 'routine'}
    return render(request, 'routine/routine_select.html', context)

# 유틸리티 함수
def parse_number(value):
    # GPT 응답 등에서 숫자만 안정적으로 추출
    match = re.findall(r'\d+', str(value))
    if not match: return 0
    elif len(match) == 1: return int(match[0])
    else: return (int(match[0]) + int(match[1])) // 2

# 2. GPT 기반 추천 루틴 생성
@login_required
def gpt_plan_view(request):
    level = request.GET.get('level', '초급')
    part = request.GET.get('part', '하체')
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    prompt = f"""
    # ... (프롬프트 내용은 기존과 동일) ...
    # 출력 형식
    한 줄에 아래 형식으로 출력하고, 총 4~6줄을 반드시 지켜라.
    "운동이름::세트::반복횟수::추천무게(kg)::상세 설명 및 꿀팁::핵심 주의사항"
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        gpt_lines = [line.strip().strip('"') for line in content.split('\n') if line.strip() and line.count('::') == 5]

        if not 4 <= len(gpt_lines) <= 6: raise ValueError("GPT가 4~6개 사이의 운동을 생성하지 못했습니다.")

        new_routine = Routine.objects.create(user=request.user, name=f"AI 추천 루틴: {part} ({level})")

        for line in gpt_lines:
            parts = line.split('::')
            if len(parts) == 6:
                name, sets, reps, weight, desc, prec = parts
                # DB에 없으면 이름으로 생성, 있으면 가져오기
                exercise, _ = Exercise.objects.get_or_create(
                    name=name.strip(),
                    defaults={'muscle_group': part, 'exercise_type': 'strength', 'gif_url': ''}
                )
                RoutineExercise.objects.create(
                    routine=new_routine, exercise=exercise,
                    sets=parse_number(sets), reps=parse_number(reps), weight=parse_number(weight),
                    description=desc.strip(), precautions=prec.strip()
                )
        
        messages.success(request, f"'{new_routine.name}' 루틴이 성공적으로 생성되었습니다!")
        return redirect('routine:routine_plan_detail', routine_id=new_routine.id)

    except Exception as e:
        messages.error(request, f"AI 루틴 생성 중 오류가 발생했습니다: {e}")
        return redirect('routine:select')

# 3. 사용자가 직접 구성한 루틴 생성
@login_required
def custom_plan_view(request):
    exercises_json = request.GET.get('exercises', '[]')
    try:
        exercise_list = json.loads(exercises_json)
    except json.JSONDecodeError:
        return redirect('routine:select')

    if not exercise_list: return redirect('routine:select')
    
    new_routine = Routine.objects.create(user=request.user, name=f"{request.user.username}님의 맞춤 루틴")
    
    for item in exercise_list:
        exercise = get_object_or_404(Exercise, name=item['name'])
        if exercise.exercise_type == 'cardio':
            RoutineExercise.objects.create(
                routine=new_routine, exercise=exercise, duration_minutes=int(item.get('duration', 0)),
                description=exercise.description, precautions=exercise.precautions
            )
        else:
            RoutineExercise.objects.create(
                routine=new_routine, exercise=exercise,
                sets=int(item.get('sets', 0)), reps=int(item.get('reps', 0)), weight=int(item.get('weight', 0)),
                description=exercise.description, precautions=exercise.precautions
            )

    messages.success(request, f"'{new_routine.name}' 루틴이 성공적으로 생성되었습니다!")
    return redirect('routine:routine_plan_detail', routine_id=new_routine.id)

# 4. 내 루틴 목록 페이지
@login_required
def my_routines_view(request):
    user_routines = Routine.objects.filter(user=request.user).order_by('-created_at')
    context = {'routines': user_routines, 'active_menu': 'routine_list'}
    return render(request, 'routine/my_routines.html', context)

# 5. 루틴 상세 보기 및 수정 페이지
@login_required
def routine_plan_detail_view(request, routine_id):
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    routine_exercises = routine.routineexercise_set.select_related('exercise').order_by('id')
    all_muscle_groups = Exercise.objects.values_list('muscle_group', flat=True).distinct()

    routine_details = []
    for re in routine_exercises:
        detail = {
            'id': re.id, 'name': re.exercise.name, 'muscle_group': re.exercise.muscle_group,
            'gif_url': re.exercise.gif_url or "기본_GIF_URL", 'exercise_type': re.exercise.exercise_type,
            'description': re.description, 'precautions': re.precautions,
        }
        if re.exercise.exercise_type == 'cardio':
            detail.update({'duration_minutes': re.duration_minutes})
        else:
            detail.update({'sets': re.sets, 'reps': re.reps, 'weight': re.weight})
        routine_details.append(detail)
    
    context = {
        'routine_obj': routine, 'routine_title': routine.name,
        'routine': routine_details, 'all_muscle_groups': all_muscle_groups,
        'active_menu': 'routine_list'
    }
    return render(request, 'routine/routine_plan_with_details.html', context)

# 6. 루틴 수정 처리
@require_POST
@login_required
def edit_routine_view(request, routine_id):
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    
    try:
        exercises_data = json.loads(request.POST.get('exercises_data', '[]'))
        new_routine_name = request.POST.get('routine_name', routine.name).strip()

        if not new_routine_name:
            messages.error(request, "루틴 이름은 비워둘 수 없습니다.")
            return redirect('routine:routine_plan_detail', routine_id=routine.id)
        
        if not exercises_data:
            messages.error(request, "루틴에는 최소 하나 이상의 운동이 포함되어야 합니다.")
            return redirect('routine:routine_plan_detail', routine_id=routine.id)

        # 기존 운동 모두 삭제 후 새로 추가 (가장 안정적인 방식)
        routine.routineexercise_set.all().delete()

        for item in exercises_data:
            exercise = get_object_or_404(Exercise, name=item['name'])
            
            if exercise.exercise_type == 'cardio':
                RoutineExercise.objects.create(
                    routine=routine, exercise=exercise,
                    duration_minutes=int(item.get('duration_minutes', 0)),
                    description=exercise.description, precautions=exercise.precautions
                )
            else:
                RoutineExercise.objects.create(
                    routine=routine, exercise=exercise,
                    sets=int(item.get('sets', 0)), reps=int(item.get('reps', 0)), weight=int(item.get('weight', 0)),
                    description=exercise.description, precautions=exercise.precautions
                )
        
        routine.name = new_routine_name
        routine.save()

        messages.success(request, "루틴이 성공적으로 수정되었습니다!")
    except Exception as e:
        messages.error(request, f"루틴 수정 중 오류가 발생했습니다: {e}")

    return redirect('routine:routine_plan_detail', routine_id=routine.id)

# 7. 루틴 삭제
@require_POST
@login_required
def delete_routine_view(request, routine_id):
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    routine_name = routine.name
    routine.delete()
    messages.success(request, f"'{routine_name}' 루틴이 삭제되었습니다.")
    return redirect('routine:my_routines')

# 8. 운동 목록 API
def exercise_api(request):
    group = request.GET.get('muscle_group')
    if not group: return JsonResponse({"error": "muscle_group 파라미터가 필요합니다."}, status=400)
    exercises = Exercise.objects.filter(muscle_group__icontains=group)
    if group == '유산소': exercises = Exercise.objects.filter(exercise_type="cardio")
    data = {"exercises": list(exercises.values('name', 'muscle_group', 'gif_url', 'exercise_type'))}
    return JsonResponse(data)

# 9. 유튜브 검색 API
def youtube_search_api(request):
    query = request.GET.get('q')
    if not query: return JsonResponse({'error': '검색어(q)가 필요합니다.'}, status=400)
    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    if not api_key: return JsonResponse({'videos': []}) # 키 없으면 빈 값 반환

    try:
        response = requests.get('https://www.googleapis.com/youtube/v3/search',
            params={'part': 'snippet', 'q': query, 'key': api_key, 'type': 'video', 'maxResults': 3})
        response.raise_for_status()
        videos = [{
            'title': item['snippet']['title'], 'video_id': item['id']['videoId'],
            'thumbnail_url': item['snippet']['thumbnails']['medium']['url'],
            'channel_title': item['snippet']['channelTitle'],
        } for item in response.json().get('items', [])]
        return JsonResponse({'videos': videos})
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)