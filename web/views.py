# web/views.py - 전체 코드를 이걸로 교체하세요.

import json
import re
from collections import OrderedDict, defaultdict
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.translation import gettext as _
from django.core.mail import send_mail
from django.conf import settings
from .models import Inquiry

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
    
    if check_and_award_achievement:
        one_year_ago = today - timezone.timedelta(days=365)
        if user.date_joined.date() <= one_year_ago:
            check_and_award_achievement(request, user, 'anniversary_1year',  extra_tags='achievement_unlocked')

    if Profile:
        try:
            profile = Profile.objects.get(user=user)
            context['profile'] = profile
        except Profile.DoesNotExist:
            context['profile'] = None

    if Profile:
        try:
            profile = Profile.objects.select_related('active_title__achievement').get(user=user)
            context['profile'] = profile
            context['active_title'] = profile.active_title
        except Profile.DoesNotExist:
            context['profile'] = None
            context['active_title'] = None

    latest_routine = None
    try:
        latest_routine = Routine.objects.filter(user=user).prefetch_related('routineexercise_set__exercise').latest('created_at')
        
        # [핵심 수정 1] 루틴 이름 분석 로직 추가
        routine_name_info = {'type': 'custom', 'name': latest_routine.name} # 기본값
        
        # 번역된 문자열을 기준으로 비교하기 위해 _() 함수 사용
        ai_pattern = _("AI 추천:")
        custom_pattern_end = _("님의 맞춤 루틴")

        if latest_routine.name.startswith(ai_pattern):
            routine_name_info['type'] = 'ai'
            # "AI 추천: " 부분을 제거한 나머지 이름
            routine_name_info['name'] = latest_routine.name[len(ai_pattern):].strip()

        elif latest_routine.name.endswith(custom_pattern_end):
            routine_name_info['type'] = 'user_custom'
            # "님의 맞춤 루틴" 부분을 제거한 사용자 이름 부분
            routine_name_info['name'] = latest_routine.name[:-len(custom_pattern_end)].strip()
        
        context['routine_name_info'] = routine_name_info

        # 운동 목록 생성 로직 (이전과 동일하게 localized_name 사용)
        exercises_in_routine = []
        for routine_ex in latest_routine.routineexercise_set.all()[:5]:
            exercise_detail = {
                'name': routine_ex.exercise.localized_name,
                'sets': routine_ex.sets,
                'reps': routine_ex.reps
            }
            exercises_in_routine.append(exercise_detail)
        context['exercises_list'] = exercises_in_routine

    except Routine.DoesNotExist:
        context['exercises_list'] = []
        context['routine_name_info'] = None
        
    context['latest_routine'] = latest_routine

    today_diet_summary = defaultdict(float)
    if Meal:
        daily_meals = Meal.objects.filter(user=user, created_at__date=today)
        for meal in daily_meals:
            if meal.analysis_result and isinstance(meal.analysis_result, dict) and 'total_nutrition' in meal.analysis_result:
                nutrition = meal.analysis_result['total_nutrition']
                today_diet_summary['total_kcal'] += parse_nutrition_value(nutrition.get('calories', 0))
                today_diet_summary['carbs'] += parse_nutrition_value(nutrition.get('carbohydrate', 0))
                today_diet_summary['protein'] += parse_nutrition_value(nutrition.get('protein', 0))
                today_diet_summary['fat'] += parse_nutrition_value(nutrition.get('fat', 0))
    context['today_diet_summary'] = dict(today_diet_summary)

    inbody_chart_data = {'labels': [], 'weights': [], 'muscles': [], 'fats': []}
    if BodyCompositionRecord:
        all_records = BodyCompositionRecord.objects.filter(user=user).order_by('created_at')
        daily_last_records = OrderedDict()
        for record in all_records:
            date_key = record.created_at.date()
            daily_last_records[date_key] = record
        final_records_list = list(daily_last_records.values())[-30:]
        inbody_chart_data['labels'] = [rec.created_at.strftime('%m/%d') for rec in final_records_list]
        inbody_chart_data['weights'] = [rec.weight for rec in final_records_list]
        inbody_chart_data['muscles'] = [rec.skeletal_muscle_mass for rec in final_records_list]
        inbody_chart_data['fats'] = [rec.body_fat_mass for rec in final_records_list]
    context['inbody_chart_data'] = json.dumps(inbody_chart_data)

    diet_chart_data = {
        'carbs': round(today_diet_summary['carbs'], 1),
        'protein': round(today_diet_summary['protein'], 1),
        'fat': round(today_diet_summary['fat'], 1),
    }
    context['diet_chart_data'] = json.dumps(diet_chart_data) 
    
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