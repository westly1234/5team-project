# chatbot/user_context.py

from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
from web.models import HealthSurvey, FitnessProfile
from routine.models import Routine, WorkoutLog
from diet.models import Meal
from achievements.models import UserAchievement 
from accounts.models import Profile
from django.utils import timezone # RuntimeWarning 해결을 위해 추가

# [핵심] Django의 번역기 대신, 우리가 만든 JSON 번역기를 가져옵니다.
from .json_translator import translate

def get_user_profile_context(user: User, lang_code='ko') -> str:
    """
    사용자의 모든 관련 데이터를 .json 파일을 직접 읽어 번역하여 생성합니다.
    """
    
    # 이제 모든 _() 호출을 translate(key, lang_code) 호출로 변경합니다.
    # 예시: _("...") -> translate("...", lang_code)
    
    if not user.is_authenticated:
        return translate("사용자 정보 없음: 비로그인 상태입니다.", lang_code)

    context_parts = [translate("### 👤 사용자 개인 프로필 및 활동 요약", lang_code)]

    # --- 1. 피트니스 프로필 (FitnessProfile) ---
    context_parts.append(translate("\n**[1. 피트니스 정보]**", lang_code))
    try:
        fp = user.fitness_profile
        profile = user.profile
        
        today = date.today()
        age_str = translate("정보 없음", lang_code)
        if fp.birth:
            age = today.year - fp.birth.year - ((today.month, today.day) < (fp.birth.month, fp.birth.day))
            age_str = translate("{age}세", lang_code).format(age=age)
        
        bmi_info = ""
        if fp.height and fp.weight:
            bmi = round(fp.weight / ((fp.height / 100) ** 2), 1)
            bmi_info = f" (BMI: {bmi})"

        context_parts.append(translate("- **기본 정보**: {age}, {gender}", lang_code).format(age=age_str, gender=fp.gender))
        context_parts.append(translate("- **신체 정보**: {height}cm, {weight}kg{bmi}", lang_code).format(height=profile.height, weight=profile.current_weight, bmi=bmi_info))
        context_parts.append(translate("- **체성분**: 골격근량 {muscle}kg, 체지방량 {fat}kg", lang_code).format(muscle=profile.skeletal_muscle_mass or translate('미입력', lang_code), fat=profile.body_fat_mass or translate('미입력', lang_code)))
        context_parts.append(translate("- **운동 목표**: {goal} (목표 체중: {target_weight}kg)", lang_code).format(goal=fp.goal, target_weight=profile.target_weight or translate('미설정', lang_code)))
        context_parts.append(translate("- **운동 경력/빈도**: {exp}, 주 {freq}회", lang_code).format(exp=fp.experience, freq=fp.frequency))
        context_parts.append(translate("- **선호 운동 타입**: {types}", lang_code).format(types=fp.types.replace(',', ', ')))
        
    except (AttributeError, FitnessProfile.DoesNotExist) if FitnessProfile else (AttributeError,):
        context_parts.append(translate("- (피트니스 프로필이 입력되지 않았습니다.)", lang_code))

    # --- 2. 건강 설문 정보 (HealthSurvey) ---
    context_parts.append(translate("\n**[2. 건강 관련 중요 정보]**", lang_code))
    try:
        hs = user.health_survey

        def format_json_list(json_data):
            if isinstance(json_data, list) and json_data:
                return ', '.join([translate(item, lang_code) for item in json_data])
            return translate("없음", lang_code)

        context_parts.append(translate("- **혈액형**: {blood_type}", lang_code).format(blood_type=hs.blood_type or translate('정보 없음', lang_code)))
        context_parts.append(translate("- **알레르기**: {allergies}", lang_code).format(allergies=format_json_list(hs.allergy)))
        if hs.allergy_details: context_parts.append(translate("  - 상세: {details}", lang_code).format(details=hs.allergy_details))
        
        context_parts.append(translate("- **지병**: {diseases}", lang_code).format(diseases=format_json_list(hs.chronic_disease)))
        if hs.chronic_disease_details: context_parts.append(translate("  - 상세: {details}", lang_code).format(details=hs.chronic_disease_details))
        
        if hs.surgery_history: context_parts.append(translate("- **수술/부상 이력**: {history}", lang_code).format(history=hs.surgery_history))
        if hs.current_medication: context_parts.append(translate("- **현재 복용 약**: {meds}", lang_code).format(meds=hs.current_medication))
        if hs.supplements: context_parts.append(translate("- **복용 중인 보조제**: {supplements}", lang_code).format(supplements=hs.supplements))
        context_parts.append(translate("- **흡연**: {status}", lang_code).format(status=hs.smoking_status))
        context_parts.append(translate("- **음주**: {freq}", lang_code).format(freq=hs.drinking_frequency))
        context_parts.append(translate("- **가족력**: {history}", lang_code).format(history=format_json_list(hs.family_history)))
        if hs.family_history_details: context_parts.append(translate("  - 상세: {details}", lang_code).format(details=hs.family_history_details))

    except (AttributeError, HealthSurvey.DoesNotExist) if HealthSurvey else (AttributeError,):
        context_parts.append(translate("- (건강 설문이 입력되지 않았습니다.)", lang_code))

    # --- 3. 최근 운동 '완료' 기록 요약 (WorkoutLog) ---
    context_parts.append(translate("\n**[3. 최근 7일간 운동 완료 기록]**", lang_code))
    try:
        recent_logs = WorkoutLog.objects.filter(
            user=user,
            completed_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('routine').order_by('-completed_at')

        if recent_logs.exists():
            for log in recent_logs:
                log_title = log.routine.name if log.routine else translate("직접 기록한 운동", lang_code)
                context_parts.append(translate("- **{date}**: {title} 완료", lang_code).format(date=log.completed_at.strftime('%y-%m-%d'), title=log_title))
        else:
            context_parts.append(translate("- 기록 없음", lang_code))
    except Exception as e:
        print(f"운동 완료 기록 조회 오류: {e}")
        context_parts.append(translate("- (기록 조회 중 오류 발생)", lang_code))

    # --- 4. 최근 식단 기록 요약 (Meal) ---
    context_parts.append(translate("\n**[4. 최근 3일간 식단 기록]**", lang_code))
    try:
        recent_meals = Meal.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(days=3)
        ).order_by('-created_at')

        if recent_meals.exists():
            for m in recent_meals:
                meal_summary = ""
                if m.analysis_result and 'foods' in m.analysis_result:
                    foods = [f"{food['name']}({food.get('calories', 'N/A')}kcal)" for food in m.analysis_result['foods']]
                    total_calories = m.analysis_result.get('total_calories', 'N/A')
                    meal_summary = translate("분석된 음식: {foods} (총 {calories}kcal)", lang_code).format(foods=', '.join(foods), calories=total_calories)
                elif m.text_input:
                    meal_summary = translate("입력된 내용: {text}", lang_code).format(text=m.text_input[:50])
                elif m.image:
                    meal_summary = translate("이미지로 기록됨 (상세 분석 정보 없음)", lang_code)
                
                context_parts.append(translate("- **{datetime}**: {summary}", lang_code).format(datetime=m.created_at.strftime('%y-%m-%d %H:%M'), summary=meal_summary))
        else:
            context_parts.append(translate("- 기록 없음", lang_code))
    except Exception as e:
        print(f"식단 기록 조회 오류: {e}")
        context_parts.append(translate("- (기록 조회 중 오류 발생)", lang_code))
    
    # --- 5. 달성한 업적 정보 (UserAchievement) ---
    context_parts.append(translate("\n**[5. 주요 달성 업적 및 칭호]**", lang_code))
    try:
        active_title_str = translate("없음", lang_code)
        if user.profile.active_title:
            active_title_str = user.profile.active_title.achievement.title_reward
        
        context_parts.append(translate("- **대표 칭호**: {title}", lang_code).format(title=active_title_str))

        recent_achievements = UserAchievement.objects.filter(user=user).select_related('achievement').order_by('-awarded_at')[:5]
        
        if recent_achievements.exists():
            ach_list = [f"'{ach.achievement.name}'" for ach in recent_achievements]
            context_parts.append(translate("- **최근 달성 업적**: {ach_list}", lang_code).format(ach_list=', '.join(ach_list)))
        else:
            context_parts.append(translate("- **최근 달성 업적**: 아직 달성한 업적이 없습니다.", lang_code))
            
    except Exception as e:
        print(f"업적 정보 조회 오류: {e}")
        context_parts.append(translate("- (업적 정보 조회 중 오류 발생)", lang_code))
        
    return "\n".join(context_parts)