# diet/views.py

import base64
import json
import re
from datetime import date, timedelta
from collections import defaultdict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .forms import MealForm
from .models import Meal
from openai import OpenAI
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

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
    당신은 전문 영양사입니다. 제공되는 음식 이미지나 텍스트를 분석하여 반드시 아래와 같은 JSON 형식으로만 응답해주세요.
    - 'foods' 리스트에는 인식된 각 음식의 이름과 예상 칼로리를 담아주세요.
    - 'total_nutrition' 객체에는 총 칼로리, 탄수화물, 단백질, 지방의 총량을 g 단위로 추정하여 담아주세요.
    - 'feedback'에는 분석된 식단에 대한 간단하고 긍정적인 피드백을 1~2문장으로 제공해주세요.

    JSON 형식 예시:
    {
      "foods": [
        {"name": "흰 쌀밥", "calories": "300kcal"},
        {"name": "김치찌개", "calories": "150kcal"}
      ],
      "total_nutrition": {
        "calories": "450kcal",
        "carbohydrate": "70g",
        "protein": "15g",
        "fat": "10g"
      },
      "feedback": "한식의 정석! 든든한 한 끼 식사네요. 단백질을 조금 더 보충하면 더욱 완벽할 거예요."
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

@login_required
def diet_analysis_view(request):
    """식단을 업로드하고 분석을 요청하는 페이지의 뷰"""
    if request.method == 'POST':
        form = MealForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. 사용자가 제출한 데이터 유효성 검사 (이미지나 텍스트 중 하나는 있어야 함)
            if not form.cleaned_data.get('image') and not form.cleaned_data.get('text_input'):
                form.add_error(None, "사진을 올리거나 글로 작성해주세요. 둘 중 하나는 필수입니다.")
                # 유효하지 않으면, 에러 메시지와 함께 폼을 다시 렌더링
                return render(request, 'diet/diet_analysis.html', {'form': form, 'active_menu': 'diet_analysis'})

            # 2. Meal 객체 생성 (아직 DB에 완전히 저장하지 않음)
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
                return redirect('diet:diet_result', meal_id=meal.id)
    
    # POST 요청이 아닐 경우 (페이지 첫 로드)
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

    # 주간 통계 계산 로직
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