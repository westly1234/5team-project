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
from datetime import date, timedelta
from django.utils import timezone

# ✅ 1. 업적 서비스 및 관련 모델 임포트
from achievements.services import check_and_award_achievement
from .models import WorkoutLog # WorkoutLog 모델도 사용하므로 명시적으로 임포트

# ==============================================================================
# ✨ 업적 트리거 함수 섹션 ✨
# (두 번째 파일에서 가져온 핵심 로직)
# ==============================================================================

def trigger_routine_creation_achievements(request, routine, routine_exercises):
    """루틴이 성공적으로 생성되었을 때 달성 가능한 업적을 확인합니다."""
    user = request.user

    # --- 루틴 생성 기본 업적 ---
    check_and_award_achievement(request, user, 'first_routine')

    routine_count = Routine.objects.filter(user=user).count()
    if routine_count >= 3:
        check_and_award_achievement(request, user, 'routine_collector_bronze')
    if routine_count >= 10:
        check_and_award_achievement(request, user, 'routine_collector_silver')

    # --- 루틴 구성 관련 업적 ---
    if len(routine_exercises) >= 5:
        check_and_award_achievement(request, user, 'comprehensive_routine')

    muscle_groups = {re.exercise.muscle_group for re in routine_exercises if re.exercise.muscle_group}
    if {'가슴', '등', '어깨'}.intersection(muscle_groups):
        check_and_award_achievement(request, user, 'upper_body_focus')
    if '하체' in muscle_groups:
        check_and_award_achievement(request, user, 'lower_body_focus')
    if '코어' in muscle_groups or '복근' in muscle_groups:
        check_and_award_achievement(request, user, 'core_focus')
        
    exercise_types = {re.exercise.exercise_type for re in routine_exercises}
    if 'strength' in exercise_types and 'cardio' in exercise_types:
        check_and_award_achievement(request, user, 'hybrid_routine')
    
    exercise_names = {re.exercise.name for re in routine_exercises}
    if {'스쿼트', '벤치프레스', '데드리프트'}.issubset(exercise_names):
        check_and_award_achievement(request, user, 'big_3_trainee')
    
    total_cardio_duration = sum(re.duration_minutes for re in routine_exercises if re.exercise.exercise_type == 'cardio' and re.duration_minutes)
    if total_cardio_duration >= 60:
        check_and_award_achievement(request, user, 'marathon_heart')


def trigger_workout_completion_achievements(request, workout_log):
    """운동을 '완료'했을 때 달성 가능한 업적을 확인합니다."""
    user = request.user
    today = timezone.now().date()
    
    check_and_award_achievement(request, user, 'first_workout_done')
    
    workout_count = WorkoutLog.objects.filter(user=user).count()
    if workout_count >= 1: check_and_award_achievement(request, user, 'workout_log_1')
    if workout_count >= 5: check_and_award_achievement(request, user, 'workout_log_5')
    if workout_count >= 10: check_and_award_achievement(request, user, 'workout_log_10')
    if workout_count >= 30: check_and_award_achievement(request, user, 'workout_log_30')
    if workout_count >= 50: check_and_award_achievement(request, user, 'workout_log_50')
    if workout_count >= 70: check_and_award_achievement(request, user, 'workout_log_70')
    if workout_count >= 100: check_and_award_achievement(request, user, 'workout_log_100')
    if workout_count >= 300: check_and_award_achievement(request, user, 'workout_log_10')
    if workout_count >= 365: check_and_award_achievement(request, user, 'workout_log_365')

    # 연속 운동 (3일, 7일 등)
    if all(WorkoutLog.objects.filter(user=user, completed_at__date=today - timedelta(days=i)).exists() for i in range(1, 4)):
        check_and_award_achievement(request, user, 'workout_streak_3')
    if all(WorkoutLog.objects.filter(user=user, completed_at__date=today - timedelta(days=i)).exists() for i in range(1, 8)):
        check_and_award_achievement(request, user, 'workout_streak_7')

    # 히든 업적 (시간, 특정일)
    hour = workout_log.completed_at.astimezone(timezone.get_current_timezone()).hour
    if 2 <= hour < 5: check_and_award_achievement(request, user, 'night_owl_workout')
    if 5 <= hour < 7: check_and_award_achievement(request, user, 'early_bird_workout')
    
    if today.month == 12 and today.day == 25: check_and_award_achievement(request, user, 'xmas_workout')
    if today.month == 1 and today.day == 1: check_and_award_achievement(request, user, 'new_year_workout')
    
    if workout_log.routine:
        exercise_types = {re.exercise.exercise_type for re in workout_log.routine.routineexercise_set.all()}
        if 'cardio' in exercise_types: check_and_award_achievement(request, user, 'first_cardio')
        if 'strength' in exercise_types: check_and_award_achievement(request, user, 'first_strength')


# ==============================================================================
# ✨ Django 뷰 함수 섹션 (기존 첫 번째 코드 기반) ✨
# ==============================================================================

# 1. 메인 루틴 선택 페이지
@login_required
def routine_select_view(request):
    context = {'active_menu': 'routine'}
    return render(request, 'routine/routine_select.html', context)

# 유틸리티 함수
def parse_number(value):
    match = re.findall(r'\d+', str(value))
    if not match: return 0
    elif len(match) == 1: return int(match[0])
    else: return (int(match[0]) + int(match[1])) // 2

# 2. GPT 기반 추천 루틴 생성 (업적 트리거 추가)
@login_required
def gpt_plan_view(request):
    # (GPT 호출 및 파싱 로직은 기존 코드와 동일)
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
    try:
        new_routine = Routine.objects.create(user=request.user, name=f"AI 추천 루틴: {part} ({level})")
        
        routine_details_for_template = []
        new_routine_exercises = [] # ✅ 업적 확인을 위해 생성된 RoutineExercise 객체를 담을 리스트

        for item in final_valid_exercises:
            # DB에 RoutineExercise 생성 후, 그 객체를 변수에 저장
            re_obj = RoutineExercise.objects.create(
                routine=new_routine, exercise=item['exercise'],
                sets=item['sets'], reps=item['reps'], weight=item['weight'],
                description=item['description'], precautions=item['precautions']
            )
            new_routine_exercises.append(re_obj) # ✅ 리스트에 추가

            routine_details_for_template.append({
                'name': item['exercise'].name, 'muscle_group': item['exercise'].muscle_group,
                'gif_url': item['exercise'].gif_url, 'exercise_type': item['exercise'].exercise_type,
                'sets': item['sets'], 'reps': item['reps'], 'weight': item['weight'],
                'description': item['description'], 'precautions': item['precautions']
            })

        # ✅ 루틴과 운동 목록이 모두 성공적으로 생성된 후 업적 트리거 호출
        if new_routine and new_routine_exercises:
            trigger_routine_creation_achievements(request, new_routine, new_routine_exercises)
            check_and_award_achievement(request, request.user, 'ai_trainer') # AI 트레이너 업적

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

# 3. 사용자가 직접 구성한 루틴 생성 (업적 트리거 추가)
@login_required
def custom_plan_view(request):
    exercises_json = request.GET.get('exercises', '[]')
    try:
        exercise_list = json.loads(exercises_json)
    except json.JSONDecodeError:
        return redirect('routine:select')

    if not exercise_list: return redirect('routine:select')
    
    new_routine = Routine.objects.create(user=request.user, name=f"{request.user.username}님의 맞춤 루틴")
    new_routine_exercises = [] # ✅ 업적 확인용 리스트

    for item in exercise_list:
        exercise = get_object_or_404(Exercise, name=item['name'])
        if exercise.exercise_type == 'cardio':
            re_obj = RoutineExercise.objects.create(
                routine=new_routine, exercise=exercise, duration_minutes=int(item.get('duration', 0)),
                description=exercise.description, precautions=exercise.precautions
            )
        else:
            re_obj = RoutineExercise.objects.create(
                routine=new_routine, exercise=exercise,
                sets=int(item.get('sets', 0)), reps=int(item.get('reps', 0)), weight=int(item.get('weight', 0)),
                description=exercise.description, precautions=exercise.precautions
            )
        new_routine_exercises.append(re_obj) # ✅ 생성된 객체 추가

    # ✅ 루틴과 운동 목록이 모두 성공적으로 생성된 후 업적 트리거 호출
    if new_routine and new_routine_exercises:
        trigger_routine_creation_achievements(request, new_routine, new_routine_exercises)

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


# ✅ 8. '운동 완료'를 처리하는 새로운 뷰 추가
@require_POST
@login_required
def workout_complete_view(request, routine_id): # 함수 이름을 URL 설정과 일치시킵니다.
    """'이 루틴 완료하기' 버튼을 눌렀을 때 호출되어 운동 기록을 남기고 업적을 확인합니다."""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    
    # 운동 완료 기록(WorkoutLog) 생성
    # user와 routine을 명시적으로 전달합니다.
    workout_log = WorkoutLog.objects.create(user=request.user, routine=routine, completed_at=timezone.now())
    
    # 운동 완료 관련 업적 트리거 함수가 있다면 호출합니다.
    # 이 함수는 request와 workout_log 객체를 인자로 받습니다.
    if callable(trigger_workout_completion_achievements):
        trigger_workout_completion_achievements(request, workout_log)
    
    messages.success(request, f"'{routine.name}' 운동을 완료했습니다! 오늘도 수고하셨습니다.")
    return redirect('routine:my_routines') # 완료 후 내 루틴 목록으로 이동


# 9. 운동 목록 API
def exercise_api(request):
    group = request.GET.get('muscle_group')
    if not group: return JsonResponse({"error": "muscle_group 파라미터가 필요합니다."}, status=400)
    exercises = Exercise.objects.filter(muscle_group__icontains=group)
    if group == '유산소': exercises = Exercise.objects.filter(exercise_type="cardio")
    data = {"exercises": list(exercises.values('name', 'muscle_group', 'gif_url', 'exercise_type'))}
    return JsonResponse(data)

# 10. 유튜브 검색 API
def youtube_search_api(request):
    query = request.GET.get('q')
    if not query: return JsonResponse({'error': '검색어(q)가 필요합니다.'}, status=400)
    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    if not api_key: return JsonResponse({'videos': []})

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