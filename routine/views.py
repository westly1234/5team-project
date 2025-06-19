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
import random

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
import random

# 2. GPT 기반 추천 루틴 생성 (무게 보정 기능 추가)
@login_required
def gpt_plan_view(request):
    level = request.GET.get('level', '초급')
    part = request.GET.get('part', '하체')
    
    available_exercises = list(Exercise.objects.filter(muscle_group=part))
    if not available_exercises:
        context = {
            'routine_title': "루틴 생성 불가", 'routine': [],
            'error': f"'{part}' 부위에 해당하는 운동이 데이터베이스에 등록되어 있지 않습니다. 관리자에게 문의하세요.",
            'active_menu': 'routine'
        }
        return render(request, 'routine/routine_plan_with_details.html', context)

    exercise_names_str = ", ".join([ex.name for ex in available_exercises])
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ✅ 1. 프롬프트 강화: 무게 항목에 숫자만 사용하도록 더욱 명확하게 지시
    prompt = f"""
    # 역할
    당신은 사용 가능한 운동 목록을 기반으로 최적의 운동 루틴을 생성하는 전문 트레이너 'Jay'입니다.

    # 지침
    1.  **반드시 "사용 가능한 운동 목록"에 있는 운동 이름만 사용하세요.** 목록에 없는 운동은 절대로 추천하지 마세요.
    2.  '{part}' 부위를 '{level}' 수준에 맞게 단련할 **4개에서 6개의 운동**을 선택하세요.
    3.  결과는 반드시 아래 <출력형식>의 예시와 같이, 각 운동을 `<운동>` 태그로 감싸고, 전체를 `<운동목록>` 태그로 감싸서 응답해야 합니다.
    4.  **무게(kg) 항목에는 반드시 숫자만 기입하세요. (예: "20", "40") 텍스트 설명은 절대 넣지 마세요.**

    # 사용 가능한 운동 목록
    {exercise_names_str}

    # <출력형식>
    <운동목록>
    <운동>"운동이름1::세트::반복횟수::무게(kg)::설명::주의사항"</운동>
    <운동>"운동이름2::세트::반복횟수::무게(kg)::설명::주의사항"</운동>
    </운동목록>
    """

    MAX_ATTEMPTS = 3
    final_valid_exercises = []

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content
            lines_from_gpt = re.findall(r'<운동>"([^"]+)"</운동>', content)
            
            validated_this_attempt = []
            found_exercise_pks = set()

            for line in lines_from_gpt:
                if line.count('::') != 5: continue
                
                parts = line.split('::')
                name, sets, reps, weight, desc, prec = parts
                exercise_name_from_gpt = name.strip()

                exercise_match = None
                for db_exercise in available_exercises:
                    if db_exercise.name in exercise_name_from_gpt:
                        exercise_match = db_exercise
                        break
                
                if exercise_match and exercise_match.pk not in found_exercise_pks:
                    # ✅ 2. 코드 레벨에서 무게 보정 로직 추가
                    weight_val = parse_number(weight)
                    if weight_val == 0:
                        if level == '초급':
                            weight_val = 10
                        elif level == '중급':
                            weight_val = 25
                        else: # '고급'
                            weight_val = 40
                    
                    validated_this_attempt.append({
                        'exercise': exercise_match, 'sets': parse_number(sets),
                        'reps': parse_number(reps), 'weight': weight_val, # 보정된 무게 값 사용
                        'description': desc.strip(), 'precautions': prec.strip()
                    })
                    found_exercise_pks.add(exercise_match.pk)
            
            if len(validated_this_attempt) >= 4:
                final_valid_exercises = validated_this_attempt
                break
        
        except Exception as e:
            print(f"🚨 AI API 호출 오류 (시도 {attempt + 1}): {e}")

    # --- 결과 보정 및 최종 처리 (기존과 동일) ---
    if len(final_valid_exercises) > 6:
        final_valid_exercises = final_valid_exercises[:6]

    if 0 < len(final_valid_exercises) < 4:
        existing_pks = {ex['exercise'].pk for ex in final_valid_exercises}
        needed = 4 - len(final_valid_exercises)
        pool = [ex for ex in available_exercises if ex.pk not in existing_pks]
        random.shuffle(pool)
        for i in range(min(needed, len(pool))):
            new_ex = pool[i]
            # 보충되는 운동에도 레벨에 맞는 기본 무게 설정
            default_weight = 10 if level == '초급' else (25 if level == '중급' else 40)
            final_valid_exercises.append({
                'exercise': new_ex, 'sets': 3, 'reps': 12, 'weight': default_weight,
                'description': new_ex.description or "기본 설명입니다.", 
                'precautions': new_ex.precautions or "기본 주의사항입니다."
            })

    if not final_valid_exercises:
        context = {
            'routine_title': "AI 루틴 생성 실패", 'routine': [],
            'error': "AI가 여러 번 시도했지만 루틴을 생성하지 못했습니다. 잠시 후 다시 시도하거나, 직접 루틴을 구성해주세요.",
            'active_menu': 'routine'
        }
        return render(request, 'routine/routine_plan_with_details.html', context)

    # --- DB 저장 및 결과 페이지 렌더링 (기존과 동일) ---
    try:
        new_routine = Routine.objects.create(user=request.user, name=f"AI 추천 루틴: {part} ({level})")
        
        routine_details_for_template = []
        for item in final_valid_exercises:
            RoutineExercise.objects.create(
                routine=new_routine, exercise=item['exercise'],
                sets=item['sets'], reps=item['reps'], weight=item['weight'],
                description=item['description'], precautions=item['precautions']
            )
            routine_details_for_template.append({
                'name': item['exercise'].name, 'muscle_group': item['exercise'].muscle_group,
                'gif_url': item['exercise'].gif_url, 'exercise_type': item['exercise'].exercise_type,
                'sets': item['sets'], 'reps': item['reps'], 'weight': item['weight'],
                'description': item['description'], 'precautions': item['precautions']
            })

        messages.success(request, f"'{new_routine.name}' 루틴이 성공적으로 생성되었습니다!")
        context = {
            'routine_obj': new_routine, 'routine_title': new_routine.name,
            'routine': routine_details_for_template, 'active_menu': 'routine',
            'all_muscle_groups': Exercise.objects.values_list('muscle_group', flat=True).distinct()
        }
        return render(request, 'routine/routine_plan_with_details.html', context)
    except Exception as e:
        context = {
            'routine_title': "루틴 저장 실패", 'routine': [],
            'error': f"루틴을 데이터베이스에 저장하는 중 오류가 발생했습니다: {e}",
            'active_menu': 'routine'
        }
        return render(request, 'routine/routine_plan_with_details.html', context)

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