# MYSITE/web/views.py

import json
import re
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from collections import OrderedDict # ✅ 날짜 순서를 유지하며 중복을 제거하기 위해 import

# --- 다른 앱의 모델 import ---
try:
    from routine.models import Routine, RoutineExercise, Exercise
except ImportError:
    Routine, RoutineExercise, Exercise = None, None, None

try:
    from diet.models import Meal
except ImportError:
    Meal = None
    
try:
    from accounts.models import BodyCompositionRecord
except ImportError:
    BodyCompositionRecord = None

# --- 헬퍼 함수 ---
def parse_nutrition_value(value_str):
    if isinstance(value_str, (int, float)): return value_str
    if isinstance(value_str, str):
        numbers = re.findall(r'\d+\.?\d*', value_str)
        if numbers: return float(numbers[0])
    return 0

# --- 기존 뷰 함수들은 그대로 유지 ---
def home(request):
    return render(request, 'web/index.html')

def health_page_view(request):
    return render(request, 'web/components/health.html')

def auth_signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '회원가입이 성공적으로 완료되었습니다. 로그인해주세요.')
            return redirect('login_page')
    else:
        form = UserCreationForm()
    return render(request, 'web/components/auth.html', {'form': form})

def workout_plan_view(request):
    return HttpResponse("<h1>운동 플랜 페이지입니다. (준비 중)</h1>")

def diet_management_view(request):
    return HttpResponse("<h1>식단 관리 페이지입니다. (준비 중)</h1>")

def nearby_places_view(request):
    return HttpResponse("<h1>주변 장소 찾기 페이지입니다. (준비 중)</h1>")

def ai_chatbot_view(request):
    return HttpResponse("<h1>AI 헬스 코치 페이지입니다. (준비 중)</h1>")

def start_trial(request):
    return render(request, 'web/start_trial.html')


# --- 대시보드 뷰 함수 (핵심 수정) ---
@login_required
def services_page(request):
    user = request.user
    today = timezone.now().date()
    
    context = {
        'user': user,
        'active_menu': 'dashboard',
    }

    # --- 1. 최근 운동 루틴 가져오기 ---
    latest_routine = None
    if Routine:
        try:
            latest_routine = Routine.objects.filter(user=user).prefetch_related('routineexercise_set__exercise').latest('created_at')
            exercises_in_routine = []
            for routine_ex in latest_routine.routineexercise_set.all()[:5]:
                exercise_detail = {
                    'name': routine_ex.exercise.name, 'sets': routine_ex.sets, 'reps': routine_ex.reps
                }
                exercises_in_routine.append(exercise_detail)
            latest_routine.exercises_list = exercises_in_routine
        except Routine.DoesNotExist:
            latest_routine = None
    context['latest_routine'] = latest_routine

    # --- 2. 오늘의 식단 요약 정보 가져오기 ---
    today_diet_summary = {'total_kcal': 0, 'carbs': 0, 'protein': 0, 'fat': 0}
    if Meal:
        daily_meals = Meal.objects.filter(user=user, created_at__date=today)
        for meal in daily_meals:
            if meal.analysis_result and isinstance(meal.analysis_result, dict) and 'total_nutrition' in meal.analysis_result:
                nutrition = meal.analysis_result['total_nutrition']
                today_diet_summary['total_kcal'] += parse_nutrition_value(nutrition.get('calories', 0))
                today_diet_summary['carbs'] += parse_nutrition_value(nutrition.get('carbohydrate', 0))
                today_diet_summary['protein'] += parse_nutrition_value(nutrition.get('protein', 0))
                today_diet_summary['fat'] += parse_nutrition_value(nutrition.get('fat', 0))
    context['today_diet_summary'] = today_diet_summary

    # --- 3. ✅ 인바디 스타일 그래프 데이터 준비 (수정된 로직) ---
    inbody_chart_data = {
        'labels': [], 'weights': [], 'muscles': [], 'fats': [],
    }
    if BodyCompositionRecord:
        # 사용자의 모든 기록을 시간 순으로 가져옵니다.
        all_records = BodyCompositionRecord.objects.filter(user=user).order_by('created_at')

        # 날짜별 마지막 기록만 저장할 OrderedDict를 사용합니다.
        daily_last_records = OrderedDict()
        for record in all_records:
            date_key = record.created_at.date()
            # 딕셔너리에 계속 덮어쓰면, 자연스럽게 그날의 마지막 기록만 남게 됩니다.
            daily_last_records[date_key] = record

        # 딕셔너리의 값(최종 레코드 객체 리스트)을 가져옵니다.
        final_records_list = list(daily_last_records.values())
        
        # 차트 가독성을 위해 최근 30개의 데이터만 사용합니다.
        if len(final_records_list) > 30:
            final_records_list = final_records_list[-30:]

        # 최종 필터링된 데이터로 차트용 리스트를 만듭니다.
        inbody_chart_data['labels'] = [rec.created_at.strftime('%m/%d') for rec in final_records_list]
        inbody_chart_data['weights'] = [rec.weight for rec in final_records_list]
        inbody_chart_data['muscles'] = [rec.skeletal_muscle_mass for rec in final_records_list]
        inbody_chart_data['fats'] = [rec.body_fat_mass for rec in final_records_list]

    context['inbody_chart_data'] = json.dumps(inbody_chart_data)

    # --- 4. 식단 구성 도넛 차트 데이터 준비 ---
    diet_chart_data = {
        'carbs': round(today_diet_summary['carbs'], 1),
        'protein': round(today_diet_summary['protein'], 1),
        'fat': round(today_diet_summary['fat'], 1),
    }
    context['diet_chart_data'] = json.dumps(diet_chart_data)
    
    # 템플릿 파일 이름을 'web/services.html'로 사용하고 있으므로 그대로 둡니다.
    return render(request, 'web/services.html', context)