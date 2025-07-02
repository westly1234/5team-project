# routine/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.utils.translation import gettext as _
from openai import OpenAI
from .models import Exercise, Routine, RoutineExercise, WorkoutLog
import json
import re
import requests
import random
from datetime import timedelta
from django.utils import timezone

from achievements.services import check_and_award_achievement
from django.utils import translation

def populate_exercise_details_if_empty(exercise: Exercise):
    """
    Exercise 객체의 설명 및 주의사항 필드가 비어있을 경우,
    OpenAI API를 호출하여 내용을 채우고 데이터베이스에 저장합니다.
    """
    # 이미 모든 주요 언어의 설명이 채워져 있다면, 함수를 즉시 종료 (API 호출 방지)
    if exercise.description and exercise.description_en and exercise.description_es:
        return

    print(f"✨ '{exercise.name}' 운동 정보가 비어있어 API를 호출하여 생성합니다...")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    # 영어 이름이 있으면 API가 더 잘 이해하므로 우선적으로 사용
    exercise_name_for_prompt = exercise.name_en or exercise.name

    prompt = f"""
    You are an expert fitness content creator.
    For the exercise "{exercise_name_for_prompt}", generate a concise 2-sentence description and 2 brief precautions.
    Provide the output ONLY in a valid JSON object format. The JSON must have keys "ko", "en", "es".
    Each language key should contain "description" and "precautions".

    Example for "Push-up":
    {{
      "ko": {{
        "description": "푸쉬업은 가슴, 어깨, 삼두근을 강화하는 대표적인 상체 운동입니다. 맨몸으로 어디서든 할 수 있어 접근성이 매우 좋습니다.",
        "precautions": "허리가 아래로 처지지 않도록 코어에 힘을 유지하세요. 팔꿈치를 몸통에 너무 붙이거나 벌리지 않도록 주의하세요."
      }},
      "en": {{
        "description": "The push-up is a classic upper body exercise that strengthens the chest, shoulders, and triceps. It's highly accessible as it can be done anywhere with no equipment.",
        "precautions": "Keep your core engaged to prevent your lower back from sagging. Avoid flaring your elbows out too wide or tucking them in too close."
      }},
      "es": {{
        "description": "La flexión es un ejercicio clásico para la parte superior del cuerpo que fortalece el pecho, los hombros y los tríceps. Es muy accesible ya que se puede hacer en cualquier lugar sin equipo.",
        "precautions": "Mantén el core activado para evitar que tu espalda baja se hunda. Evita abrir demasiado los codos o pegarlos demasiado al cuerpo."
      }}
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            # ✨ JSON 응답을 강제하여 파싱 안정성 확보
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)

        # 데이터베이스 필드 업데이트
        exercise.description = data.get('ko', {}).get('description', '설명을 생성하지 못했습니다.')
        exercise.precautions = data.get('ko', {}).get('precautions', '주의사항을 생성하지 못했습니다.')
        
        exercise.description_en = data.get('en', {}).get('description', 'Failed to generate description.')
        exercise.precautions_en = data.get('en', {}).get('precautions', 'Failed to generate precautions.')
        
        exercise.description_es = data.get('es', {}).get('description', 'No se pudo generar la descripción.')
        exercise.precautions_es = data.get('es', {}).get('precautions', 'No se pudieron generar las precauciones.')
        
        # 변경된 내용을 데이터베이스에 저장
        exercise.save()
        print(f"✅ '{exercise.name}' 운동 정보가 성공적으로 생성 및 저장되었습니다.")

    except Exception as e:
        # API 호출 실패 시, 에러를 출력하고 프로그램은 계속 진행되도록 함
        print(f"🚨 OpenAI API 호출 중 오류 발생: {e}")

# ==============================================================================
# ✨ 업적 트리거 함수 섹션 ✨
# ==============================================================================

def trigger_routine_creation_achievements(request, routine, routine_exercises):
    user = request.user
    check_and_award_achievement(request, user, 'first_routine')
    routine_count = Routine.objects.filter(user=user).count()
    if routine_count >= 3: check_and_award_achievement(request, user, 'routine_collector_bronze')
    if routine_count >= 10: check_and_award_achievement(request, user, 'routine_collector_silver')
    if len(routine_exercises) >= 5: check_and_award_achievement(request, user, 'comprehensive_routine')
    muscle_groups = {re.exercise.muscle_group for re in routine_exercises if re.exercise.muscle_group}
    if {'가슴', '등', '어깨'}.intersection(muscle_groups): check_and_award_achievement(request, user, 'upper_body_focus')
    if '하체' in muscle_groups: check_and_award_achievement(request, user, 'lower_body_focus')
    if '코어' in muscle_groups or '복근' in muscle_groups: check_and_award_achievement(request, user, 'core_focus')
    exercise_types = {re.exercise.exercise_type for re in routine_exercises}
    if 'strength' in exercise_types and 'cardio' in exercise_types: check_and_award_achievement(request, user, 'hybrid_routine')
    exercise_names = {re.exercise.name for re in routine_exercises}
    if {'스쿼트', '벤치프레스', '데드리프트'}.issubset(exercise_names): check_and_award_achievement(request, user, 'big_3_trainee')
    total_cardio_duration = sum(re.duration_minutes for re in routine_exercises if re.exercise.exercise_type == 'cardio' and re.duration_minutes)
    if total_cardio_duration >= 60: check_and_award_achievement(request, user, 'marathon_heart')


def trigger_workout_completion_achievements(request, workout_log):
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
    if workout_count >= 300: check_and_award_achievement(request, user, 'workout_log_300')
    if workout_count >= 365: check_and_award_achievement(request, user, 'workout_log_365')
    if all(WorkoutLog.objects.filter(user=user, completed_at__date=today - timedelta(days=i)).exists() for i in range(1, 4)): check_and_award_achievement(request, user, 'workout_streak_3')
    if all(WorkoutLog.objects.filter(user=user, completed_at__date=today - timedelta(days=i)).exists() for i in range(1, 8)): check_and_award_achievement(request, user, 'workout_streak_7')
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
# ✨ Django 뷰 함수 섹션 ✨
# ==============================================================================

@login_required
def routine_select_view(request):
    """루틴 생성 메인 페이지 뷰"""
    return render(request, 'routine/routine_select.html', {'active_menu': 'routine'})


def parse_number(value):
    """문자열에서 숫자를 추출하는 유틸리티 함수"""
    match = re.findall(r'\d+', str(value))
    if not match: return 0
    return int(match[0]) if len(match) == 1 else (int(match[0]) + int(match[1])) // 2


@login_required
def gpt_plan_view(request):
    level_from_request = request.GET.get('level', '초급')
    part_from_request = request.GET.get('part', '하체')

    # [핵심 수정] 스페인어 번역이 정확히 일치하는지 확인하고 추가
    PART_TRANSLATION_MAP = {
        # 한국어 (기본)
        '하체': '하체', '등': '등', '가슴': '가슴', '어깨': '어깨', '팔': '팔', '복근': '복근',
        # 영어
        'Legs': '하체', 'Back': '등', 'Chest': '가슴', 'Shoulders': '어깨', 'Arms': '팔', 'Abs': '복근',
        # 스페인어 (실제 .po 파일의 번역과 일치시켜야 함)
        'Piernas': '하체', 
        'Espalda': '등', 
        'Pecho': '가슴', 
        'Hombros': '어깨', 
        'Brazos': '팔', 
        'Abdominales': '복근',
    }
    LEVEL_TRANSLATION_MAP = {
        # 한국어 (기본)
        '초급': '초급', '중급': '중급', '고급': '고급',
        # 영어
        'Beginner': '초급', 'Intermediate': '중급', 'Advanced': '고급',
        # 스페인어 (실제 .po 파일의 번역과 일치시켜야 함)
        'Principiante': '초급', 
        'Intermedio': '중급', 
        'Avanzado': '고급',
    }
    
    db_part = PART_TRANSLATION_MAP.get(part_from_request, part_from_request)
    db_level = LEVEL_TRANSLATION_MAP.get(level_from_request, level_from_request)

    available_exercises = list(Exercise.objects.filter(muscle_group=db_part))
    
    if not available_exercises:
        context = {
            'routine_title': _("루틴 생성 불가"), 'routine': [],
            'error': _("'%(part)s' 부위에 해당하는 운동이 데이터베이스에 등록되어 있지 않습니다. 관리자에게 문의하세요.") % {'part': part_from_request},
            'active_menu': 'routine'
        }
        return render(request, 'routine/routine_plan_with_details.html', context)

    exercise_names_str = ", ".join([ex.name for ex in available_exercises])
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    prompt = f"""
    # 역할: 당신은 사용 가능한 운동 목록을 기반으로 최적의 운동 루틴을 생성하는 전문 트레이너 'Jay'입니다.
    # 지침:
    1. **반드시 "사용 가능한 운동 목록"에 있는 운동 이름만 사용하세요.** 목록에 없는 운동은 절대로 추천하지 마세요.
    2. '{db_part}' 부위를 '{db_level}' 수준에 맞게 단련할 **4개에서 6개의 운동**을 선택하세요.
    3. 결과는 반드시 아래 <출력형식>의 예시와 같이, 각 운동을 `<운동>` 태그로 감싸고, 전체를 `<운동목록>` 태그로 감싸서 응답해야 합니다.
    4. **무게(kg) 항목에는 반드시 숫자만 기입하세요. (예: "20", "40")**
    # 사용 가능한 운동 목록: {exercise_names_str}
    # <출력형식>: <운동목록><운동>"운동이름1::세트::반복횟수::무게(kg)::설명::주의사항"</운동>...</운동목록>
    """
    
    MAX_ATTEMPTS = 3
    final_valid_exercises = []
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
            content = response.choices[0].message.content
            lines_from_gpt = re.findall(r'<운동>"([^"]+)"</운동>', content)
            validated_this_attempt = []
            found_exercise_pks = set()
            for line in lines_from_gpt:
                if line.count('::') != 5: continue
                parts = [p.strip() for p in line.split('::')]
                name, sets, reps, weight, desc, prec = parts
                exercise_match = next((ex for ex in available_exercises if ex.name in name), None)
                if exercise_match and exercise_match.pk not in found_exercise_pks:
                    weight_val = parse_number(weight) or (10 if db_level == '초급' else (25 if db_level == '중급' else 40))
                    validated_this_attempt.append({'exercise': exercise_match, 'sets': parse_number(sets), 'reps': parse_number(reps), 'weight': weight_val, 'description': desc, 'precautions': prec})
                    found_exercise_pks.add(exercise_match.pk)
            if len(validated_this_attempt) >= 4:
                final_valid_exercises = validated_this_attempt
                break
        except Exception as e:
            print(f"🚨 AI API 호출 오류 (시도 {attempt + 1}): {e}")

    if 0 < len(final_valid_exercises) < 4:
        existing_pks = {ex['exercise'].pk for ex in final_valid_exercises}
        needed = 4 - len(final_valid_exercises)
        pool = [ex for ex in available_exercises if ex.pk not in existing_pks]
        random.shuffle(pool)
        for i in range(min(needed, len(pool))):
            new_ex = pool[i]
            default_weight = 10 if db_level == '초급' else (25 if db_level == '중급' else 40)
            final_valid_exercises.append({'exercise': new_ex, 'sets': 3, 'reps': 12, 'weight': default_weight, 'description': new_ex.description or "", 'precautions': new_ex.precautions or ""})

    if not final_valid_exercises:
        context = {'routine_title': _("AI 루틴 생성 실패"), 'routine': [], 'error': _("AI가 루틴을 생성하지 못했습니다. 잠시 후 다시 시도해주세요."), 'active_menu': 'routine'}
        return render(request, 'routine/routine_plan_with_details.html', context)

    try:
        with transaction.atomic():
            routine_name = _("AI 추천: %(part)s (%(level)s)") % {'part': part_from_request, 'level': level_from_request}
            new_routine = Routine.objects.create(user=request.user, name=routine_name)
            new_routine_exercises = []
            for item in final_valid_exercises:
                re_obj = RoutineExercise.objects.create(routine=new_routine, exercise=item['exercise'], sets=item['sets'], reps=item['reps'], weight=item['weight'], description=item['description'], precautions=item['precautions'])
                new_routine_exercises.append(re_obj)
            if new_routine and new_routine_exercises:
                trigger_routine_creation_achievements(request, new_routine, new_routine_exercises)
                check_and_award_achievement(request, request.user, 'ai_trainer')

        messages.success(request, _("'%s' 루틴이 성공적으로 생성되었습니다!") % new_routine.name)
        return redirect('routine:routine_plan_detail', routine_id=new_routine.id)
    except Exception as e:
        context = {'routine_title': _("루틴 저장 실패"), 'routine': [], 'error': _("루틴 저장 중 오류 발생: %(error)s") % {'error': e}, 'active_menu': 'routine'}
        return render(request, 'routine/routine_plan_with_details.html', context)


@login_required
def custom_plan_view(request):
    """사용자가 직접 구성한 루틴 생성 뷰"""
    exercises_json = request.GET.get('exercises', '[]')
    try:
        exercise_list = json.loads(exercises_json)
        if not exercise_list:
            messages.warning(request, _("최소 하나 이상의 운동을 선택해주세요."))
            return redirect('routine:select')

        with transaction.atomic():
            routine_name = _("%(username)s님의 맞춤 루틴") % {'username': request.user.username}
            new_routine = Routine.objects.create(user=request.user, name=routine_name)
            new_routine_exercises = []
            for item in exercise_list:
                exercise = get_object_or_404(Exercise, id=item.get('id'))
                if exercise.exercise_type == 'cardio':
                    re_obj = RoutineExercise.objects.create(routine=new_routine, exercise=exercise, duration_minutes=int(item.get('duration', 0)))
                else:
                    re_obj = RoutineExercise.objects.create(routine=new_routine, exercise=exercise, sets=int(item.get('sets', 0)), reps=int(item.get('reps', 0)), weight=int(item.get('weight', 0)))
                new_routine_exercises.append(re_obj)
            if new_routine and new_routine_exercises:
                trigger_routine_creation_achievements(request, new_routine, new_routine_exercises)
        
        messages.success(request, _("'%s' 루틴이 성공적으로 생성되었습니다!") % new_routine.name)
        return redirect('routine:routine_plan_detail', routine_id=new_routine.id)
    except (json.JSONDecodeError, Exercise.DoesNotExist):
        messages.error(request, _("잘못된 요청입니다."))
        return redirect('routine:select')


@login_required
def my_routines_view(request):
    """내 루틴 목록 페이지 뷰"""
    user_routines = Routine.objects.filter(user=request.user).prefetch_related('routineexercise_set__exercise').order_by('-created_at')
    return render(request, 'routine/my_routines.html', {'routines': user_routines, 'active_menu': 'routine_list'})


@login_required
def routine_plan_detail_view(request, routine_id):
    """루틴 상세 보기 페이지 뷰"""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    routine_exercises = routine.routineexercise_set.select_related('exercise').order_by('id')
    all_muscle_groups = sorted(list(set(ex.localized_muscle_group for ex in Exercise.objects.all() if ex.localized_muscle_group)))

    routine_details = []
    for re in routine_exercises:
        exercise = re.exercise
        
        # ✨ [핵심 수정] 운동 정보를 사용하기 전에, 정보가 비어있으면 채워넣는 함수를 호출합니다.
        populate_exercise_details_if_empty(exercise)
        
        detail = {
            'exercise_id': exercise.id,
            'name': exercise.localized_name,
            'muscle_group': exercise.localized_muscle_group,
            'gif_url': exercise.get_final_gif_url,
            'exercise_type': exercise.exercise_type,
            'description': exercise.localized_description, # 이제 이 값은 None이 아님
            'precautions': exercise.localized_precautions, # 이제 이 값은 None이 아님
        }
        if exercise.exercise_type == 'cardio':
            detail.update({'duration_minutes': re.duration_minutes})
        else:
            detail.update({'sets': re.sets, 'reps': re.reps, 'weight': re.weight})
        routine_details.append(detail)
    
    context = {
        'routine_obj': routine,
        'routine_title': routine.name,
        'routine': routine_details,
        'all_muscle_groups': all_muscle_groups,
        'active_menu': 'routine_list'
    }
    return render(request, 'routine/routine_plan_with_details.html', context)


@require_POST
@login_required
def edit_routine_view(request, routine_id):
    """루틴 수정 처리 뷰"""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    try:
        exercises_data = json.loads(request.POST.get('exercises_data', '[]'))
        new_routine_name = request.POST.get('routine_name', routine.name).strip()

        if not new_routine_name:
            messages.error(request, _("루틴 이름은 비워둘 수 없습니다."))
            return redirect('routine:routine_plan_detail', routine_id=routine.id)
        if not exercises_data:
            messages.error(request, _("루틴에는 최소 하나 이상의 운동이 포함되어야 합니다."))
            return redirect('routine:routine_plan_detail', routine_id=routine.id)

        with transaction.atomic():
            routine.routineexercise_set.all().delete()
            new_routine_exercises = []
            
            # [문제 2 해결] 프론트엔드에서 보낸 ID로 운동을 찾아 재생성
            for item in exercises_data:
                exercise_id = item.get('id')
                if not exercise_id: continue
                
                exercise = get_object_or_404(Exercise, id=exercise_id)
                if exercise.exercise_type == 'cardio':
                    re_obj = RoutineExercise.objects.create(routine=routine, exercise=exercise, duration_minutes=int(item.get('duration_minutes', 0)))
                else:
                    re_obj = RoutineExercise.objects.create(routine=routine, exercise=exercise, sets=int(item.get('sets', 0)), reps=int(item.get('reps', 0)), weight=int(item.get('weight', 0)))
                new_routine_exercises.append(re_obj)
            
            routine.name = new_routine_name
            routine.save()

            if routine and new_routine_exercises:
                trigger_routine_creation_achievements(request, routine, new_routine_exercises)

        messages.success(request, _("루틴이 성공적으로 수정되었습니다!"))
    except (json.JSONDecodeError, Exercise.DoesNotExist):
        messages.error(request, _("루틴 수정 중 잘못된 데이터가 감지되었습니다."))
    except Exception as e:
        messages.error(request, _("루틴 수정 중 오류가 발생했습니다: %(error)s") % {'error': e})

    return redirect('routine:routine_plan_detail', routine_id=routine.id)


@require_POST
@login_required
def delete_routine_view(request, routine_id):
    """루틴 삭제 처리 뷰"""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    routine_name = routine.name
    routine.delete()
    messages.success(request, _("'%s' 루틴이 삭제되었습니다.") % routine_name)
    return redirect('routine:my_routines')


@require_POST
@login_required
def workout_complete_view(request, routine_id):
    """운동 완료 처리 뷰"""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    workout_log = WorkoutLog.objects.create(user=request.user, routine=routine, completed_at=timezone.now())
    trigger_workout_completion_achievements(request, workout_log)
    messages.success(request, _("'%s' 운동을 완료했습니다! 오늘도 수고하셨습니다.") % routine.name)
    return redirect('routine:my_routines')


def exercise_api(request):
    """운동 라이브러리 목록을 반환하는 API"""
    group_key = request.GET.get('muscle_group')
    if not group_key:
        return JsonResponse({"error": "muscle_group parameter is required."}, status=400)

    MUSCLE_GROUP_MAP = {'legs': '하체', 'back': '등', 'chest': '가슴', 'shoulders': '어깨', 'arms': '팔', 'abs': '복근'}
    if group_key == 'cardio':
        exercises_qs = Exercise.objects.filter(exercise_type="cardio")
    elif group_key in MUSCLE_GROUP_MAP:
        korean_group_name = MUSCLE_GROUP_MAP[group_key]
        exercises_qs = Exercise.objects.filter(muscle_group=korean_group_name)
    else:
        exercises_qs = Exercise.objects.none()

    exercises_list = []
    for ex in exercises_qs:
        exercises_list.append({
            'id': ex.id,
            'name': ex.localized_name,
            'muscle_group': ex.localized_muscle_group,
            'gif_url': ex.get_final_gif_url,
            'exercise_type': ex.exercise_type
        })
    return JsonResponse({"exercises": exercises_list})


def youtube_search_api(request):
    """유튜브 검색 결과를 반환하는 API"""
    query = request.GET.get('q')
    if not query: return JsonResponse({'error': 'Query (q) is required.'}, status=400)
    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    if not api_key: return JsonResponse({'videos': []})
    try:
        response = requests.get('https://www.googleapis.com/youtube/v3/search', params={'part': 'snippet', 'q': query, 'key': api_key, 'type': 'video', 'maxResults': 3})
        response.raise_for_status()
        videos = [{'title': item['snippet']['title'], 'video_id': item['id']['videoId'], 'thumbnail_url': item['snippet']['thumbnails']['medium']['url'], 'channel_title': item['snippet']['channelTitle']} for item in response.json().get('items', [])]
        return JsonResponse({'videos': videos})
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)



@require_POST
@login_required
def analyze_routine_api(request, routine_id):
    """AI 루틴 분석 결과를 사용자의 현재 언어에 맞춰 반환하는 API"""
    get_object_or_404(Routine, id=routine_id, user=request.user)

    try:
        # 1. 현재 언어 코드 가져오기
        lang = translation.get_language()  # 'ko', 'en', 'es' 등

        # 2. 각 언어별 프롬프트와 단위(unit) 텍스트 정의
        PROMPT_TEMPLATES = {
            'ko': {
                'system_prompt': """
                당신은 국내 최고의 피트니스 분석 전문가입니다. 사용자가 제공한 운동 루틴을 분석하고, 예상되는 효과와 조언을 친절하고 이해하기 쉽게 설명해야 합니다.
                **분석 가이드라인:**
                1. **전체 요약:** 루틴 전체의 목표를 한두 문장으로 요약하세요.
                2. **주요 타겟 근육:** 루틴이 주로 어떤 근육 부위를 발달시키는지 설명해주세요.
                3. **예상 효과:** 루틴을 통해 얻을 수 있는 긍정적 효과들을 항목별로 설명합니다.
                4. **팁 및 조언:** 더 효과적인 수행을 위한 팁이나 주의사항을 1~2가지 추가해주세요.
                5. **출력 형식:** 전체 답변은 마크다운(Markdown) 형식을 사용하고, 이모티콘(💪, 🔥, 🥗)을 적절히 사용하여 동기를 부여하는 톤으로 작성해주세요.
                """,
                'user_prompt_template': "아래 운동 루틴을 분석해주세요:\n\n{routine_text}",
                'unit_sets': '세트', 'unit_reps': '회', 'unit_minutes': '분', 'unit_kg': 'kg'
            },
            'en': {
                'system_prompt': """
                You are a top-tier fitness analysis expert. You must analyze the user-provided workout routine and explain the expected effects and advice in a friendly and easy-to-understand manner.
                **Analysis Guidelines:**
                1. **Overall Summary:** Summarize the routine's goal in one or two sentences.
                2. **Main Target Muscles:** Explain which muscle groups the routine primarily develops.
                3. **Expected Effects:** Describe the positive effects of the routine by item.
                4. **Tips & Advice:** Add 1-2 tips or precautions for more effective performance.
                5. **Output Format:** Use Markdown for the entire response and use emojis (💪, 🔥, 🥗) appropriately to create a motivating tone.
                """,
                'user_prompt_template': "Please analyze the following workout routine:\n\n{routine_text}",
                'unit_sets': 'sets', 'unit_reps': 'reps', 'unit_minutes': 'min', 'unit_kg': 'kg'
            },
            'es': {
                'system_prompt': """
                Eres un experto analista de fitness de primer nivel. Debes analizar la rutina de ejercicios proporcionada por el usuario y explicar los efectos esperados y consejos de una manera amigable y fácil de entender.
                **Guía de Análisis:**
                1. **Resumen General:** Resume el objetivo de la rutina en una o dos frases.
                2. **Músculos Principales:** Explica qué grupos musculares desarrolla principalmente la rutina.
                3. **Efectos Esperados:** Describe los efectos positivos de la rutina por puntos.
                4. **Consejos y Recomendaciones:** Añade 1-2 consejos o precauciones para un rendimiento más efectivo.
                5. **Formato de Salida:** Usa Markdown para toda la respuesta y utiliza emojis (💪, 🔥, 🥗) apropiadamente para crear un tono motivador.
                """,
                'user_prompt_template': "Por favor, analiza la siguiente rutina de ejercicios:\n\n{routine_text}",
                'unit_sets': 'series', 'unit_reps': 'repeticiones', 'unit_minutes': 'min', 'unit_kg': 'kg'
            }
        }
        
        # 3. 현재 언어에 맞는 템플릿 선택 (지원하지 않는 언어일 경우 영어로 대체)
        templates = PROMPT_TEMPLATES.get(lang, PROMPT_TEMPLATES['en'])

        exercises_data = json.loads(request.body)
        if not exercises_data:
            return JsonResponse({'error': 'No exercise data to analyze.'}, status=400)
        
        # 4. 현재 언어에 맞는 단위(unit)를 사용하여 routine_text 구성
        routine_text = ""
        for i, ex in enumerate(exercises_data):
            # ex['name']은 이미 localized_name을 통해 현재 언어로 전달됨
            if ex.get('duration_minutes'):
                routine_text += f"{i+1}. {ex['name']}: {ex['duration_minutes']}{templates['unit_minutes']}\n"
            else:
                routine_text += f"{i+1}. {ex['name']}: {ex['sets']} {templates['unit_sets']} x {ex['reps']} {templates['unit_reps']}, {ex['weight']}{templates['unit_kg']}\n"
        
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # 5. 선택된 템플릿으로 최종 프롬프트 생성
        system_prompt = templates['system_prompt']
        user_prompt = templates['user_prompt_template'].format(routine_text=routine_text)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": user_prompt}
            ], 
            temperature=0.7
        )
        
        analysis_result = response.choices[0].message.content
        return JsonResponse({'analysis': analysis_result})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid data format.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'AI analysis error: {str(e)}'}, status=500)