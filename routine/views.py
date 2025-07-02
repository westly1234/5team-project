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

# routine/views.py

# routine/views.py

@login_required
def routine_select_view(request):
    """루틴 생성 메인 페이지 뷰"""
    
    # [핵심 수정] 이 부분을 여기에 추가해야 합니다!
    # 템플릿에서 사용할 운동 부위와 난이도 목록을 생성합니다.
    body_parts = [
        {'key': 'legs', 'name': _('하체')},
        {'key': 'back', 'name': _('등')},
        {'key': 'chest', 'name': _('가슴')},
        {'key': 'shoulders', 'name': _('어깨')},
        {'key': 'arms', 'name': _('팔')},
        {'key': 'abs', 'name': _('복근')},
    ]
    levels = [
        {'key': 'beginner', 'name': _('초급')},
        {'key': 'intermediate', 'name': _('중급')},
        {'key': 'advanced', 'name': _('고급')},
    ]

    # 생성한 목록을 context에 담아 템플릿으로 전달합니다.
    context = {
        'active_menu': 'routine',
        'body_parts': body_parts,
        'levels': levels,
    }
    
    return render(request, 'routine/routine_select.html', context)

def parse_number(value):
    """문자열에서 숫자를 추출하는 유틸리티 함수"""
    match = re.findall(r'\d+', str(value))
    if not match: return 0
    return int(match[0]) if len(match) == 1 else (int(match[0]) + int(match[1])) // 2


# routine/views.py

# routine/views.py

@login_required
def gpt_plan_view(request):
    # [1단계] 언어에 독립적인 고정 key 값을 받음
    part_key = request.GET.get('part', 'legs')
    level_key = request.GET.get('level', 'beginner')

    # [2단계] 고정 key를 DB가 이해하는 한국어 값으로 변환하는 간단한 맵
    PART_KEY_TO_DB = {
        'legs': '하체', 'back': '등', 'chest': '가슴',
        'shoulders': '어깨', 'arms': '팔', 'abs': '복근'
    }
    LEVEL_KEY_TO_DB = {
        'beginner': '초급', 'intermediate': '중급', 'advanced': '고급'
    }
    
    db_part = PART_KEY_TO_DB.get(part_key, '하체')
    db_level = LEVEL_KEY_TO_DB.get(level_key, '초급')
    
    # [3단계] DB에서 운동 목록 조회
    available_exercises = list(Exercise.objects.filter(muscle_group=db_part))

    # DB에 운동이 아예 없는 경우에 대한 유일한 실패 처리
    if not available_exercises:
        # 화면에 표시될 번역된 부위 이름 찾기 (첫 번째 운동 객체에서 가져옴)
        display_part_name = PART_KEY_TO_DB.get(part_key, _('알 수 없는 부위')) # Fallback
        for part_info in request.routine_select_view_context['body_parts']:
            if part_info['key'] == part_key:
                display_part_name = part_info['name']
                break
        
        context = {
            'routine_title': _("루틴 생성 불가"), 'routine': [],
            'error': _("죄송합니다. 현재 '%(part)s' 부위에 추천할 수 있는 운동이 준비되지 않았습니다.") % {'part': display_part_name},
            'active_menu': 'routine'
        }
        return render(request, 'routine/routine_plan_with_details.html', context)

    # [4단계] GPT 루틴 생성 시도
    final_valid_exercises = []
    try:
        exercise_names_str = ", ".join([f'"{ex.name}"' for ex in available_exercises])
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = f"""
        당신은 전문가 트레이너입니다. 다음 "사용 가능 운동" 목록에서 '{db_part}' 부위를 위한 '{db_level}' 수준의 운동 4-6개를 선택하여 루틴을 만드세요.
        반드시 아래 XML 형식으로만 응답하고, 다른 말은 절대 추가하지 마세요.
        
        # 사용 가능 운동:
        {exercise_names_str}

        # 출력 형식:
        <Routines>
          <Exercise name="운동이름1" sets="3" reps="12" weight="20" description="간단한 설명" precautions="간단한 주의사항"/>
          <Exercise name="운동이름2" sets="4" reps="10" weight="50" description="간단한 설명" precautions="간단한 주의사항"/>
        </Routines>
        """
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        content = response.choices[0].message.content
        matches = re.findall(r'<Exercise\s+name="([^"]+)"\s+sets="([^"]+)"\s+reps="([^"]+)"\s+weight="([^"]+)"\s+description="([^"]+)"\s+precautions="([^"]+)"\s*/>', content)
        
        found_pks = set()
        for match in matches:
            name, sets, reps, weight, desc, prec = match
            exercise_match = next((ex for ex in available_exercises if ex.name == name), None)
            if exercise_match and exercise_match.pk not in found_pks:
                final_valid_exercises.append({'exercise': exercise_match, 'sets': parse_number(sets), 'reps': parse_number(reps), 'weight': parse_number(weight), 'description': desc, 'precautions': prec})
                found_pks.add(exercise_match.pk)
    except Exception as e:
        print(f"🚨 GPT API 오류 발생. DB 기반으로 루틴을 생성합니다: {e}")
        final_valid_exercises = []

    # [5단계] "무조건 생성"을 위한 최종 안전장치
    if len(final_valid_exercises) < 4:
        print(f"⚠️ GPT 결과가 부족하거나 실패하여 DB 기반으로 루틴을 강제 생성합니다.")
        final_valid_exercises = [] # 혹시 모를 부분 성공을 대비해 리스트 초기화
        random.shuffle(available_exercises)
        
        num_exercises_to_create = random.randint(4, min(6, len(available_exercises)))
        
        for ex in available_exercises[:num_exercises_to_create]:
            default_sets, default_reps, default_weight = (3, 12, 10) # 기본값
            if db_level == '중급': default_weight = 25
            elif db_level == '고급': default_weight = 40
            
            final_valid_exercises.append({
                'exercise': ex, 'sets': default_sets, 'reps': default_reps, 'weight': default_weight,
                'description': ex.localized_description or "", 'precautions': ex.localized_precautions or ""
            })

    # [6단계] 루틴 저장 및 리디렉션
    try:
        with transaction.atomic():
            # 화면 표시용 번역된 이름 가져오기
            display_part_name = _(db_part)
            display_level_name = _(db_level)
            
            routine_name = _("AI 추천: %(part)s (%(level)s)") % {'part': display_part_name, 'level': display_level_name}
            new_routine = Routine.objects.create(user=request.user, name=routine_name)
            
            new_routine_exercises = []
            for item in final_valid_exercises:
                re_obj = RoutineExercise.objects.create(routine=new_routine, exercise=item['exercise'], sets=item['sets'], reps=item['reps'], weight=item['weight'], description=item['description'], precautions=item['precautions'])
                new_routine_exercises.append(re_obj)
            
            trigger_routine_creation_achievements(request, new_routine, new_routine_exercises)
            check_and_award_achievement(request, request.user, 'ai_trainer')

        messages.success(request, _("'%s' 루틴이 성공적으로 생성되었습니다!") % new_routine.name)
        return redirect('routine:routine_plan_detail', routine_id=new_routine.id)
    except Exception as e:
        context = {'routine_title': _("루틴 저장 실패"), 'routine': [], 'error': _("루틴 저장 중 오류가 발생했습니다: %(error)s") % {'error': str(e)}, 'active_menu': 'routine'}
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


# routine/views.py 의 routine_plan_detail_view 함수

@login_required
def routine_plan_detail_view(request, routine_id):
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    routine_exercises = routine.routineexercise_set.select_related('exercise').order_by('id')
    all_muscle_groups = sorted(list(set(ex.localized_muscle_group for ex in Exercise.objects.all() if ex.localized_muscle_group)))

    routine_details = []
    # [추가] JavaScript에서 사용할 운동 정보 리스트
    exercises_for_js = []

    for re in routine_exercises:
        exercise = re.exercise
        populate_exercise_details_if_empty(exercise)
        
        detail = {
            'exercise_id': exercise.id,
            'name': exercise.localized_name,
            'muscle_group': exercise.localized_muscle_group,
            'gif_url': exercise.get_final_gif_url,
            'exercise_type': exercise.exercise_type,
            'description': exercise.localized_description,
            'precautions': exercise.localized_precautions,
        }
        if exercise.exercise_type == 'cardio':
            detail.update({'duration_minutes': re.duration_minutes})
        else:
            detail.update({'sets': re.sets, 'reps': re.reps, 'weight': re.weight})
        
        routine_details.append(detail)
        
        # [추가] exercises_for_js 리스트에 필요한 정보만 담기
        exercises_for_js.append({
            'id': exercise.id,
            'name': exercise.localized_name,
            'muscle_group': exercise.localized_muscle_group,
            'gif_url': exercise.get_final_gif_url,
            'exercise_type': exercise.exercise_type,
        })
    
    context = {
        'routine_obj': routine,
        'routine_title': routine.name,
        'routine': routine_details,
        'all_muscle_groups': all_muscle_groups,
        # [추가] JSON으로 변환하여 템플릿에 전달
        'exercises_for_js': json.dumps(exercises_for_js),
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