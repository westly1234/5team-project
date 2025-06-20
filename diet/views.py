# diet/views.py

import base64
import json
import re
from datetime import date, timedelta
from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .forms import MealForm
from .models import Meal
from openai import OpenAI
from django.http import JsonResponse
# ✅ 1. 업적 확인을 위한 헬퍼 함수 임포트
from achievements.services import check_and_award_achievement

# settings.py에 저장된 API 키를 사용하여 OpenAI 클라이언트 초기화
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def parse_nutrition_value(value_str):
    """'50g', '450kcal' 같은 문자열에서 숫자만 추출하는 헬퍼 함수"""
    if isinstance(value_str, (int, float)):
        return value_str
    if isinstance(value_str, str):
        numbers = re.findall(r'\d+\.?\d*', value_str)
        if numbers:
            return float(numbers[0])
    return 0 # 숫자를 찾지 못하면 0을 반환

def get_image_base64(image_file):
    """업로드된 이미지 파일을 Base64 문자열로 인코딩하는 헬퍼 함수"""
    return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_meal_with_openai(meal):
    """Meal 객체를 받아 OpenAI API를 호출하고 분석 결과를 문자열로 반환"""
    content = []
    
    prompt_text = """
    당신은 데이터를 기반으로 정확한 분석을 수행하는 전문 영양사입니다. 제공되는 정보를 다음 분석 우선순위에 따라 분석하고, 반드시 아래 JSON 형식으로만 응답해주세요.

    # 분석 우선순위
    1.  **(1순위) 이미지 내 영양성분표:** 이미지에 영양성분표가 명확하게 보인다면, 해당 수치를 최우선으로 사용합니다.
    2.  **(2순위) 특정 제품 정보 검색:** 이미지 속 음식이 특정 브랜드의 제품으로 식별되면, 웹 검색을 통해 해당 제품의 '공식 영양 정보'를 찾아 적용합니다. (예: '매일유업 춘식이 바나나우유 영양성분')
    3.  **(3순위) 일반 음식 데이터베이스:** 위 두 가지 방법으로 파악이 어려운 일반 음식(예: 제육볶음)은 신뢰도 높은 영양 데이터베이스를 기반으로 평균값을 추정합니다.

    # JSON 출력 형식
    - 'foods' 리스트에는 인식된 각 음식의 이름과 칼로리를 담아주세요.
    - 'total_nutrition' 객체에는 총 칼로리, 탄수화물, 단백질, 지방의 총량을 g 단위로 담아주세요.
    - 'feedback'에는 분석된 식단에 대한 간단하고 긍정적인 피드백을 1~2문장으로 제공해주세요.

    # JSON 형식 예시
    {
      "foods": [
        {"name": "매일유업 춘식이 바나나우유", "calories": "145kcal"}
      ],
      "total_nutrition": {
        "calories": "145kcal",
        "carbohydrate": "23g",
        "protein": "5g",
        "fat": "4.1g"
      },
      "feedback": "달콤한 바나나우유로 간편하게 에너지를 보충할 수 있어요! 즐거운 간식 시간이네요."
    }
    """
    content.append({"type": "text", "text": prompt_text})
    
    if meal.image:
        base64_image = get_image_base64(meal.image)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
    
    if meal.text_input:
        content.append({"type": "text", "text": f"사용자 텍스트 설명: {meal.text_input}"})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=1024,
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API 호출 중 오류 발생: {e}")
        return None

# ✅ 2. 업적 트리거 함수 (코드를 깔끔하게 분리)
def trigger_diet_achievements(request, meal, analysis_data):
    """
    한 번의 식단 기록으로 달성할 수 있는 모든 업적을 확인하고 부여합니다.
    """
    user = request.user

    # --- 단순/누적 기록 업적 ---
    check_and_award_achievement(request, user, 'first_meal_record') # 첫 숟갈
    if meal.image:
        check_and_award_achievement(request, user, 'first_photo_meal') # 찰칵! 첫 기록
    
    # 누적 기록 횟수 확인 (확장된 버전)
    meal_count = Meal.objects.filter(user=user).count()
    if meal_count >= 10:
        check_and_award_achievement(request, user, 'meal_record_10')   # 식단 기록가 (브론즈)
    if meal_count >= 50:
        check_and_award_achievement(request, user, 'meal_record_50')   # 식단 기록가 (실버)
    if meal_count >= 100:
        check_and_award_achievement(request, user, 'meal_record_100')  # 식단 기록가 (골드)
    if meal_count >= 365:
        check_and_award_achievement(request, user, 'meal_record_365')  # 식단 기록가 (플래티넘)

    # --- 내용 기반 업적 (AI 분석 결과 필요) ---
    if analysis_data and 'total_nutrition' in analysis_data:
        nutrition = analysis_data['total_nutrition']
        
        protein_g = parse_nutrition_value(nutrition.get('protein', 0))
        if protein_g >= 30:
            check_and_award_achievement(request, user, 'protein_hunter') # 단백질 사냥꾼

        calories_kcal = parse_nutrition_value(nutrition.get('calories', 0))
        if calories_kcal >= 1000:
            check_and_award_achievement(request, user, 'cheating_day') # 오늘은 치팅데이!

        if calories_kcal > 0: # 총 칼로리가 0 이상일 때만 계산
            carbs_g = parse_nutrition_value(nutrition.get('carbohydrate', 0))
            fat_g = parse_nutrition_value(nutrition.get('fat', 0))

            # 각 영양소의 칼로리 계산 (탄/단: 4kcal/g, 지: 9kcal/g)
            carb_calories = carbs_g * 4
            protein_calories = protein_g * 4
            fat_calories = fat_g * 9

            # 총 칼로리 대비 각 영양소 칼로리 비율 계산
            carb_ratio = (carb_calories / calories_kcal) * 100
            protein_ratio = (protein_calories / calories_kcal) * 100
            fat_ratio = (fat_calories / calories_kcal) * 100

            # 이상적인 범위 안에 들어오는지 확인 (예: 탄 40-70%, 단 10-40%, 지 15-40%)
            if (40 <= carb_ratio <= 70 and
                10 <= protein_ratio <= 40 and
                15 <= fat_ratio <= 40):
                check_and_award_achievement(request, user, 'golden_ratio_meal')

    # --- 하루 기록 업적 ---
    today_meals_count = Meal.objects.filter(user=user, created_at__date=date.today()).count()
    if today_meals_count >= 3:
        check_and_award_achievement(request, user, 'perfect_day_meals') # 완벽한 하루

# ✅ 3. 연속 기록 업적 확인을 위한 별도 함수
def check_streak_achievements(request):
    """
    연속 식단 기록 관련 업적을 확인합니다.
    (대시보드 방문 시 호출)
    """
    user = request.user
    today = date.today()

    # 7일 연속 기록 확인
    is_7_day_streak = all(Meal.objects.filter(user=user, created_at__date=today - timedelta(days=i)).exists() for i in range(7))
    if is_7_day_streak:
        check_and_award_achievement(request, user, 'diet_streak_7') # 주간 식단 챌린지
        
        # 7일 달성 시, 30일도 확인
        is_30_day_streak = all(Meal.objects.filter(user=user, created_at__date=today - timedelta(days=i)).exists() for i in range(30))
        if is_30_day_streak:
            check_and_award_achievement(request, user, 'diet_streak_30') # 한 달의 식단 마스터


@login_required
def diet_analysis_view(request):
    """식단을 업로드하고 분석을 요청하는 페이지의 뷰"""
    if request.method == 'POST':
        form = MealForm(request.POST, request.FILES)
        if form.is_valid():
            if not form.cleaned_data.get('image') and not form.cleaned_data.get('text_input'):
                form.add_error(None, "사진을 올리거나 글로 작성해주세요. 둘 중 하나는 필수입니다.")
                return render(request, 'diet/diet_analysis.html', {'form': form, 'active_menu': 'diet_analysis'})
            
            meal = form.save(commit=False)
            meal.user = request.user
            # ✅ 신규: 'meal_time' 필드 추가 (HTML 폼에서 전달받음)
            meal.meal_time = request.POST.get('meal_time', '기타')
            meal.save() # 이 시점에 meal.id가 생성됨

            # 3. OpenAI API를 호출하여 식단 분석 실행
            analysis_json_str = analyze_meal_with_openai(meal)

            # 4. 분석 결과에 따라 meal 객체 업데이트
            if analysis_json_str:
                try:
                    # 성공적으로 JSON을 파싱한 경우
                    analysis_data = json.loads(analysis_json_str)
                    meal.analysis_result = analysis_data
                    meal.save() # 분석 결과를 포함하여 최종 저장
                    print(f"✅ 식단 ID({meal.id}) 분석 성공. 결과 페이지로 이동합니다.")
                    return redirect('diet:diet_result', meal_id=meal.id)
                
                except json.JSONDecodeError:
                    # API가 이상한 텍스트(JSON이 아닌)를 반환한 경우
                    error_info = {"error": "API가 유효한 JSON을 반환하지 않았습니다.", "raw_response": analysis_json_str}
                    meal.analysis_result = error_info
                    meal.save()
                    print(f"🚨 식단 ID({meal.id}) 분석 실패 (JSON 파싱 오류). 결과 페이지로 이동합니다.")
                    return redirect('diet:diet_result', meal_id=meal.id)
            else:
                # analyze_meal_with_openai 함수 자체가 None을 반환한 경우 (API 키 오류 등)
                error_info = {"error": "AI 서버와의 통신에 실패했습니다. API 키나 네트워크 상태를 확인해주세요."}
                meal.analysis_result = error_info
                meal.save()
                print(f"🚨 식단 ID({meal.id}) 분석 실패 (API 통신 오류). 결과 페이지로 이동합니다.")
                # ✅ 4. 업적 달성 로직 호출!
                trigger_diet_achievements(request, meal, analysis_data)
                
                return redirect('diet:diet_result', meal_id=meal.id)
    else:
        form = MealForm()
        
    context = {
        'form': form,
        'active_menu': 'diet_analysis'
    }
    return render(request, 'diet/diet_analysis.html', context)

@login_required
def diet_result_view(request, meal_id):
    """단일 분석 결과를 보여주는 페이지의 뷰"""
    meal = get_object_or_404(Meal, id=meal_id, user=request.user)
    context = {
        'meal': meal,
        'active_menu': 'diet_analysis'
    }
    return render(request, 'diet/diet_result.html', context)

@login_required
def diet_report_view(request):
    """일별/주간 식단 리포트를 보여주는 대시보드 뷰"""
    
    # ✅ 5. 사용자가 이 페이지에 들어올 때 연속 기록 업적을 체크합니다.
    check_streak_achievements(request)
    
    selected_date_str = request.GET.get('date', date.today().isoformat())
    try:
        selected_date = date.fromisoformat(selected_date_str)
    except (ValueError, TypeError):
        selected_date = date.today()

    # --- 1. 일일 요약 데이터 준비 ---
    daily_meals = Meal.objects.filter(user=request.user, created_at__date=selected_date).order_by('created_at')
    
    daily_totals = defaultdict(float)
    for meal in daily_meals:
        if meal.analysis_result and 'total_nutrition' in meal.analysis_result:
            nutrition = meal.analysis_result['total_nutrition']
            daily_totals['calories'] += parse_nutrition_value(nutrition.get('calories', 0))
            daily_totals['carbohydrate'] += parse_nutrition_value(nutrition.get('carbohydrate', 0))
            daily_totals['protein'] += parse_nutrition_value(nutrition.get('protein', 0))
            daily_totals['fat'] += parse_nutrition_value(nutrition.get('fat', 0))

    # --- 2. 주간 그래프 및 통계 데이터 준비 ---
    today = date.today()
    start_date = today - timedelta(days=6)
    
    recent_meals = Meal.objects.filter(
        user=request.user, 
        created_at__date__range=[start_date, today]
    )
    
    weekly_data = defaultdict(lambda: {'calories': 0})
    for meal in recent_meals:
        if meal.analysis_result and 'total_nutrition' in meal.analysis_result:
            meal_date = meal.created_at.date()
            calories = parse_nutrition_value(meal.analysis_result['total_nutrition'].get('calories', 0))
            weekly_data[meal_date]['calories'] += calories

    graph_labels, calorie_data = [], []
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        graph_labels.append(current_date.strftime('%m/%d'))
        calorie_data.append(weekly_data[current_date]['calories'])

    total_weekly_calories = sum(calorie_data)
    days_with_meals = sum(1 for cal in calorie_data if cal > 0)
    average_calories = total_weekly_calories / days_with_meals if days_with_meals > 0 else 0
    
    max_calories = 0
    min_calories = float('inf')
    highest_day = None
    lowest_day = None

    valid_calorie_days = [(graph_labels[i], cal) for i, cal in enumerate(calorie_data) if cal > 0]
    if valid_calorie_days:
        max_calories = max(cal for _, cal in valid_calorie_days)
        min_calories = min(cal for _, cal in valid_calorie_days)
        highest_day = [label for label, cal in valid_calorie_days if cal == max_calories][0]
        lowest_day = [label for label, cal in valid_calorie_days if cal == min_calories][0]

    weekly_summary = {
        'average': average_calories,
        'highest': {'day': highest_day, 'calories': max_calories},
        'lowest': {'day': lowest_day, 'calories': min_calories if min_calories != float('inf') else 0},
    }

    context = {
        'selected_date': selected_date,
        'daily_meals': daily_meals,
        'daily_totals': daily_totals,
        'graph_labels': json.dumps(graph_labels),
        'calorie_data': json.dumps(calorie_data),
        'weekly_summary': weekly_summary,
        'active_menu': 'diet_report'
    }
    
    return render(request, 'diet/diet_report.html', context)

@login_required
@require_http_methods(["DELETE"]) # DELETE 요청만 허용
def delete_meal_view(request, meal_id):
    try:
        # 현재 로그인한 사용자의 식사 기록만 삭제할 수 있도록 필터링
        meal = Meal.objects.get(id=meal_id, user=request.user)
        meal.delete()
        return JsonResponse({'success': True})
    except Meal.DoesNotExist:
        return JsonResponse({'success': False, 'error': '해당 기록을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)