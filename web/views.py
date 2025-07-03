# web/views.py - 전체 코드를 이걸로 교체하세요.

import json
import re
from collections import OrderedDict, defaultdict
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone 
from django.utils.translation import gettext as _
from django.core.mail import send_mail
from django.conf import settings
from .models import Inquiry, DailyHealthMetric

# --- 다른 앱의 모델 및 서비스 import (기존 코드와 동일) ---
try:
    from routine.models import Routine
except ImportError:
    Routine = None

try:
    from diet.models import Meal
except ImportError:
    Meal = None
    
try:
    from accounts.models import BodyCompositionRecord, Profile, UserAchievement 
except ImportError:
    BodyCompositionRecord, Profile, UserAchievement = None, None, None

try:
    from achievements.services import check_and_award_achievement
except ImportError:
    check_and_award_achievement = None


# --- 헬퍼 함수 (기존 코드와 동일) ---
def parse_nutrition_value(value_str):
    if isinstance(value_str, (int, float)):
        return value_str
    if isinstance(value_str, str):
        numbers = re.findall(r'\d+\.?\d*', value_str)
        if numbers:
            return float(numbers[0])
    return 0


# --- 기본 뷰 함수 (기존 코드와 동일) ---
def home(request):
    return render(request, 'web/index.html')

def health_page_view(request):
    return render(request, 'web/components/health.html')

def auth_signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
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


# --- 대시보드 뷰 함수 (기존 코드와 동일) ---
@login_required
def services_page(request):
    user = request.user
    today = timezone.now().date()
    
    context = {
        'user': user,
        'active_menu': 'dashboard',
    }
    
    # 1. 1주년 업적 확인 (기존 로직 유지)
    one_year_ago = today - timezone.timedelta(days=365)
    if user.date_joined.date() <= one_year_ago:
        # check_and_award_achievement 함수가 존재할 경우에만 호출
        if callable(check_and_award_achievement):
            check_and_award_achievement(request, user, 'anniversary_1year', extra_tags='achievement_unlocked')

    # 2. 프로필 및 활성 칭호 정보 가져오기
    try:
        profile = Profile.objects.select_related('active_title__achievement').get(user=user)
        context['profile'] = profile
        context['active_title'] = profile.active_title
    except Profile.DoesNotExist:
        context['profile'] = None
        context['active_title'] = None

    # 3. 최근 운동 루틴 정보 가져오기
    try:
        latest_routine = Routine.objects.filter(user=user).prefetch_related('routineexercise_set__exercise').latest('created_at')
        
        routine_name_info = {'type': 'custom', 'name': latest_routine.name}
        ai_pattern = _("AI 추천:")
        custom_pattern_end = _("님의 맞춤 루틴")

        if latest_routine.name.startswith(ai_pattern):
            routine_name_info['type'] = 'ai'
            routine_name_info['name'] = latest_routine.name[len(ai_pattern):].strip()
        elif latest_routine.name.endswith(custom_pattern_end):
            routine_name_info['type'] = 'user_custom'
            routine_name_info['name'] = latest_routine.name[:-len(custom_pattern_end)].strip()
        
        context['routine_name_info'] = routine_name_info
        context['exercises_list'] = [
            {'name': re.exercise.localized_name, 'sets': re.sets, 'reps': re.reps}
            for re in latest_routine.routineexercise_set.all()[:5]
        ]
        context['latest_routine'] = latest_routine
    except Routine.DoesNotExist:
        context['exercises_list'] = []
        context['routine_name_info'] = None
        context['latest_routine'] = None
        
    # 4. 오늘의 식단 요약 정보 가져오기
    today_diet_summary = defaultdict(float)
    daily_meals = Meal.objects.filter(user=user, created_at__date=today)
    for meal in daily_meals:
        if meal.analysis_result and isinstance(meal.analysis_result, dict) and 'total_nutrition' in meal.analysis_result:
            nutrition = meal.analysis_result['total_nutrition']
            today_diet_summary['total_kcal'] += parse_nutrition_value(nutrition.get('calories', 0))
            today_diet_summary['carbs'] += parse_nutrition_value(nutrition.get('carbohydrate', 0))
            today_diet_summary['protein'] += parse_nutrition_value(nutrition.get('protein', 0))
            today_diet_summary['fat'] += parse_nutrition_value(nutrition.get('fat', 0))
    context['today_diet_summary'] = dict(today_diet_summary)
    context['diet_chart_data'] = json.dumps({
        'carbs': round(today_diet_summary['carbs'], 1),
        'protein': round(today_diet_summary['protein'], 1),
        'fat': round(today_diet_summary['fat'], 1),
    })

    # --- ✨ 5. [핵심 수정] 건강 지표 차트 데이터 준비 ---
    # BodyCompositionRecord 대신 DailyHealthMetric 모델을 사용합니다.
    metrics = DailyHealthMetric.objects.filter(
        user=user,
        date__gte=today - timedelta(days=30)
    ).order_by('date')

    chart_labels = []
    weight_data = []
    muscle_data = []
    fat_data = []

    if metrics.exists():
        # 모든 OS에서 작동하는 표준 형식으로 변경
        chart_labels = [m.date.strftime('%m/%d') for m in metrics]
        
        # 데이터가 None일 경우, JavaScript의 null로 변환하여 차트 선이 끊어지게 합니다.
        weight_data = [round(m.weight, 1) if m.weight is not None else 'null' for m in metrics]
        muscle_data = [round(m.skeletal_muscle_mass, 1) if m.skeletal_muscle_mass is not None else 'null' for m in metrics]
        fat_data = [round(m.body_fat_mass, 1) if m.body_fat_mass is not None else 'null' for m in metrics]
            
    # JSON으로 변환하여 템플릿에 전달합니다.
    # 기존 'inbody_chart_data' 대신, 각 데이터를 개별 키로 전달하여 템플릿에서 사용하기 쉽게 합니다.
    context['chart_labels'] = json.dumps(chart_labels)
    context['weight_data'] = json.dumps(weight_data)
    context['muscle_data'] = json.dumps(muscle_data)
    context['fat_data'] = json.dumps(fat_data)
    # ----------------------------------------------------
    
    return render(request, 'web/services.html', context)

# --- 고객 지원 관련 뷰 ---

def support_view(request):
    """고객 지원 FAQ 페이지를 보여주는 뷰"""
    return render(request, 'web/support.html')


def inquiry_view(request):
    """1:1 문의 폼을 보여주고, 제출된 문의를 처리하는 뷰"""
    
    if request.method == 'POST':
        inquiry_user = request.user if request.user.is_authenticated else None
        
        user_email = request.POST.get('email')
        subject = request.POST.get('subject')

        Inquiry.objects.create(
            user=inquiry_user,
            category=request.POST.get('category'),
            email=user_email,
            subject=subject,
            message=request.POST.get('message')
        )

        messages.success(request, '문의가 성공적으로 접수되었습니다. 빠른 시일 내에 답변드리겠습니다.')

        try:
            email_subject = f"[HealthWise] '{subject}' 문의가 정상적으로 접수되었습니다."
            email_message = f"""
안녕하세요, HealthWise입니다.

고객님의 소중한 문의가 성공적으로 접수되었습니다.
담당자가 내용을 확인한 후, 최대한 빠른 시일 내에 답변드리겠습니다.

더 나은 서비스를 만드는 데 도움을 주셔서 감사합니다.

- HealthWise 드림 -
"""
            send_mail(
                subject=email_subject,
                message=email_message,
                from_email=None,
                recipient_list=[user_email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"사용자에게 접수 확인 메일 발송 실패: {e}")

        # 'web' 그룹에 속한 'support' URL로 이동합니다.
        return redirect('web:support')

    return render(request, 'web/inquiry.html')