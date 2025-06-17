# MYSITE/web/views.py

import json
import re # 정규표현식 모듈
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum

# --- 다른 앱의 모델 import ---
try:
    from routine.models import Routine, RoutineExercise, Exercise
except ImportError:
    Routine, RoutineExercise, Exercise = None, None, None

try:
    from diet.models import Meal
except ImportError:
    Meal = None
    
# --- (1) 헬퍼 함수를 뷰 바깥으로 이동 (전역 헬퍼 함수로 변경) ---
# 이렇게 하면 뷰 함수 내의 변수와 충돌할 위험이 없습니다.
def parse_nutrition_value(value_str):
    """'50g', '450kcal' 같은 문자열에서 숫자만 추출하는 헬퍼 함수"""
    if isinstance(value_str, (int, float)):
        return value_str
    if isinstance(value_str, str):
        # 여기서 re는 항상 상단에서 import한 정규표현식 모듈을 가리킵니다.
        numbers = re.findall(r'\d+\.?\d*', value_str)
        if numbers:
            return float(numbers[0])
    return 0 # 숫자를 찾지 못하면 0을 반환

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

# --- 대시보드 뷰 함수 (오류 수정) ---

@login_required
def services_page(request):
    user = request.user
    today = timezone.now().date()
    context = {}

    # --- 1. 최근 운동 루틴 가져오기 ---
    latest_routine = None
    if Routine:
        try:
            latest_routine = Routine.objects.filter(user=user).prefetch_related('routineexercise_set__exercise').latest('created_at')
            exercises_in_routine = []
            
            # --- (2) 루틴 순회 시 변수명을 're'에서 'routine_ex'로 변경 ---
            # 're'라는 변수명은 정규표현식 모듈과 충돌하므로 사용하지 않는 것이 좋습니다.
            for routine_ex in latest_routine.routineexercise_set.all()[:5]:
                exercise_detail = {
                    'name': routine_ex.exercise.name,
                    'sets': routine_ex.sets,
                    'reps': routine_ex.reps
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
                # 이제 이 함수는 뷰 바깥에 정의된 안전한 헬퍼 함수를 호출합니다.
                today_diet_summary['total_kcal'] += parse_nutrition_value(nutrition.get('calories', 0))
                today_diet_summary['carbs'] += parse_nutrition_value(nutrition.get('carbohydrate', 0))
                today_diet_summary['protein'] += parse_nutrition_value(nutrition.get('protein', 0))
                today_diet_summary['fat'] += parse_nutrition_value(nutrition.get('fat', 0))
    context['today_diet_summary'] = today_diet_summary

    # --- 3. 체중 변화 차트 데이터 준비 ---
    weight_chart_data = {
        'labels': ['5/12', '5/13', '5/14', '5/15', '5/16', '5/17', '5/18'],
        'weights': [75.5, 75.1, 74.8, 74.9, 74.2, 73.8, 73.5]
    }
    context['weight_chart_data'] = json.dumps(weight_chart_data)

    # --- 4. 식단 구성 도넛 차트 데이터 준비 ---
    diet_chart_data = {
        'carbs': round(today_diet_summary['carbs'], 1),
        'protein': round(today_diet_summary['protein'], 1),
        'fat': round(today_diet_summary['fat'], 1),
    }
    context['diet_chart_data'] = json.dumps(diet_chart_data)
    
    return render(request, 'web/services.html', context)