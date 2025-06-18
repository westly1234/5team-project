# chatbot/user_context.py

from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
from web.models import HealthSurvey, FitnessProfile
from routine.models import Routine
from diet.models import Meal


def get_user_profile_context(user: User) -> str:
    """
    사용자의 모든 관련 데이터(FitnessProfile, HealthSurvey, 운동, 식단)를
    하나의 종합적인 텍스트 컨텍스트로 생성합니다.
    """
    if not user.is_authenticated:
        return "사용자 정보 없음: 비로그인 상태입니다."

    context_parts = ["### 👤 사용자 개인 프로필 및 활동 요약"]

    # --- 1. 피트니스 프로필 (FitnessProfile) ---
    context_parts.append("\n**[1. 피트니스 정보]**")
    try:
        fp = user.fitness_profile  # user.fitness_profile로 바로 접근
        
        # 나이 계산
        today = date.today()
        age = "정보 없음"
        if fp.birth:
            age = today.year - fp.birth.year - ((today.month, today.day) < (fp.birth.month, fp.birth.day))
            age = f"{age}세"
        
        bmi_info = ""
        if fp.height and fp.weight:
            bmi = round(fp.weight / ((fp.height / 100) ** 2), 1)
            bmi_info = f" (BMI: {bmi})"

        context_parts.append(f"- **기본 정보**: {age}, {fp.gender}")
        context_parts.append(f"- **신체 정보**: {fp.height}cm, {fp.weight}kg{bmi_info}")
        context_parts.append(f"- **운동 목표**: {fp.goal} ({fp.goal_text or '상세 목표 없음'})")
        context_parts.append(f"- **운동 경력/빈도**: {fp.experience}, 주 {fp.frequency}회")
        context_parts.append(f"- **선호 운동 타입**: {fp.types.replace(',', ', ')}") # 쉼표 뒤에 공백 추가
        
    except (AttributeError, FitnessProfile.DoesNotExist) if FitnessProfile else (AttributeError,):
        context_parts.append("- (피트니스 프로필이 입력되지 않았습니다.)")


    # --- 2. 건강 설문 정보 (HealthSurvey) ---
    context_parts.append("\n**[2. 건강 관련 중요 정보]**")
    try:
        hs = user.health_survey # user.health_survey로 바로 접근

        # JSONField로 저장된 리스트를 보기 좋게 변환하는 헬퍼 함수
        def format_json_list(json_data):
            if isinstance(json_data, list) and json_data:
                return ', '.join(map(str, json_data))
            return "없음"

        context_parts.append(f"- **혈액형**: {hs.blood_type or '정보 없음'}")
        context_parts.append(f"- **알레르기**: {format_json_list(hs.allergy)}")
        if hs.allergy_details: context_parts.append(f"  - 상세: {hs.allergy_details}")
        
        context_parts.append(f"- **지병**: {format_json_list(hs.chronic_disease)}")
        if hs.chronic_disease_details: context_parts.append(f"  - 상세: {hs.chronic_disease_details}")
        
        if hs.surgery_history: context_parts.append(f"- **수술/부상 이력**: {hs.surgery_history}")
        if hs.current_medication: context_parts.append(f"- **현재 복용 약**: {hs.current_medication}")
        if hs.supplements: context_parts.append(f"- **복용 중인 보조제**: {hs.supplements}")

        # 흡연 및 음주 정보
        context_parts.append(f"- **흡연**: {hs.smoking_status}")
        context_parts.append(f"- **음주**: {hs.drinking_frequency}")
        
        context_parts.append(f"- **가족력**: {format_json_list(hs.family_history)}")
        if hs.family_history_details: context_parts.append(f"  - 상세: {hs.family_history_details}")

    except (AttributeError, HealthSurvey.DoesNotExist) if HealthSurvey else (AttributeError,):
        context_parts.append("- (건강 설문이 입력되지 않았습니다.)")


    # --- 3. 최근 운동 기록 요약 (Routine) ---
    context_parts.append("\n**[3. 최근 7일간 운동 기록]**")
    try:
        recent_routines = Routine.objects.filter(
            user=user,
            created_at__gte=datetime.now() - timedelta(days=7)
        ).order_by('-created_at')

        if recent_routines.exists():
            for r in recent_routines:
                exercise_details = []
                for re in r.routineexercise_set.all():
                    detail = f"{re.exercise.name}"
                    if re.exercise.exercise_type == 'strength' and all([re.sets, re.reps]):
                        detail += f"({re.sets}x{re.reps}, {re.weight or 0}kg)"
                    elif re.exercise.exercise_type == 'cardio' and re.duration_minutes:
                        detail += f"({re.duration_minutes}분)"
                    exercise_details.append(detail)
                
                exercises_summary = ", ".join(exercise_details)
                context_parts.append(f"- **{r.created_at.strftime('%y-%m-%d')}**: {r.name} - [{exercises_summary}]")
        else:
            context_parts.append("- 기록 없음")
    except Exception as e:
        print(f"운동 기록 조회 오류: {e}")
        context_parts.append("- (기록 조회 중 오류 발생)")


    # --- 4. 최근 식단 기록 요약 (Meal) ---
    context_parts.append("\n**[4. 최근 3일간 식단 기록]**")
    try:
        recent_meals = Meal.objects.filter(
            user=user,
            created_at__gte=datetime.now() - timedelta(days=3)
        ).order_by('-created_at')

        if recent_meals.exists():
            for m in recent_meals:
                meal_summary = ""
                if m.analysis_result and 'foods' in m.analysis_result:
                    foods = [f"{food['name']}({food.get('calories', 'N/A')}kcal)" for food in m.analysis_result['foods']]
                    total_calories = m.analysis_result.get('total_calories', 'N/A')
                    meal_summary = f"분석된 음식: {', '.join(foods)} (총 {total_calories}kcal)"
                elif m.text_input:
                    meal_summary = f"입력된 내용: {m.text_input[:50]}"
                elif m.image:
                    meal_summary = "이미지로 기록됨 (상세 분석 정보 없음)"
                
                context_parts.append(f"- **{m.created_at.strftime('%y-%m-%d %H:%M')}**: {meal_summary}")
        else:
            context_parts.append("- 기록 없음")
    except Exception as e:
        print(f"식단 기록 조회 오류: {e}")
        context_parts.append("- (기록 조회 중 오류 발생)")
        
    return "\n".join(context_parts)