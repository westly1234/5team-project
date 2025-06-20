# web/views.py

import json
import re
from collections import OrderedDict, defaultdict # ✅ 두 파일에서 사용된 컬렉션 모두 import
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

# --- 다른 앱의 모델 및 서비스 import ---
try:
    from routine.models import Routine
except ImportError:
    Routine = None

try:
    from diet.models import Meal
except ImportError:
    Meal = None
    
try:
    from accounts.models import BodyCompositionRecord, Profile # ✅ Profile 모델 추가
except ImportError:
    BodyCompositionRecord, Profile = None, None

try:
    from achievements.services import check_and_award_achievement # ✅ 업적 서비스 추가
except ImportError:
    check_and_award_achievement = None


# --- 헬퍼 함수 ---
def parse_nutrition_value(value_str):
    """'50g', '450kcal' 같은 문자열에서 숫자만 추출하는 헬퍼 함수"""
    if isinstance(value_str, (int, float)):
        return value_str
    if isinstance(value_str, str):
        numbers = re.findall(r'\d+\.?\d*', value_str)
        if numbers:
            return float(numbers[0])
    return 0


# --- 기본 뷰 함수 ---
def home(request):
    return render(request, 'web/index.html')

def health_page_view(request):
    return render(request, 'web/components/health.html')

# ✅ 회원가입 뷰에 '첫 방문' 업적 추가
def auth_signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 회원가입 성공 시 업적 부여
            if check_and_award_achievement:
                check_and_award_achievement(request, user, 'first_visit',  extra_tags='achievement_unlocked')
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


# --- 대시보드 뷰 함수 (통합 버전) ---
@login_required
def services_page(request):
    user = request.user
    today = timezone.now().date()
    
    context = {
        'user': user,
        'active_menu': 'dashboard',
    }
    
    # ✅ 1주년 기념 업적 확인 (두 번째 파일 기능)
    if check_and_award_achievement:
        one_year_ago = today - timezone.timedelta(days=365)
        if user.date_joined.date() <= one_year_ago:
            check_and_award_achievement(request, user, 'anniversary_1year',  extra_tags='achievement_unlocked')

    # ✅ 프로필 및 칭호 정보 가져오기 (두 번째 파일 기능)
    if Profile:
        try:
            profile = Profile.objects.select_related('active_title__achievement').get(user=user)
            context['profile'] = profile
            context['active_title'] = profile.active_title
        except Profile.DoesNotExist:
            context['profile'] = None
            context['active_title'] = None

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
    today_diet_summary = defaultdict(float) # defaultdict 사용으로 코드 간소화
    if Meal:
        daily_meals = Meal.objects.filter(user=user, created_at__date=today)
        for meal in daily_meals:
            if meal.analysis_result and isinstance(meal.analysis_result, dict) and 'total_nutrition' in meal.analysis_result:
                nutrition = meal.analysis_result['total_nutrition']
                today_diet_summary['total_kcal'] += parse_nutrition_value(nutrition.get('calories', 0))
                today_diet_summary['carbs'] += parse_nutrition_value(nutrition.get('carbohydrate', 0))
                today_diet_summary['protein'] += parse_nutrition_value(nutrition.get('protein', 0))
                today_diet_summary['fat'] += parse_nutrition_value(nutrition.get('fat', 0))
    context['today_diet_summary'] = dict(today_diet_summary) # 템플릿 호환성을 위해 일반 dict로 변환

    # --- 3. 인바디 차트 데이터 준비 (더 정교한 첫 번째 파일 로직 사용) ---
    inbody_chart_data = {'labels': [], 'weights': [], 'muscles': [], 'fats': []}
    if BodyCompositionRecord:
        all_records = BodyCompositionRecord.objects.filter(user=user).order_by('created_at')
        
        # 날짜별 마지막 기록만 필터링 (OrderedDict 활용)
        daily_last_records = OrderedDict()
        for record in all_records:
            date_key = record.created_at.date()
            daily_last_records[date_key] = record

        # 최종 기록 리스트 (최대 30개로 제한)
        final_records_list = list(daily_last_records.values())[-30:]
        
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
    # ✅ 변수명 통일: _json 접미사를 제거하여 템플릿 호환성 확보
    context['diet_chart_data'] = json.dumps(diet_chart_data) 
    
    return render(request, 'web/services.html', context)