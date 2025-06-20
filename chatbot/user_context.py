# chatbot/user_context.py

from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
from web.models import HealthSurvey, FitnessProfile
from routine.models import Routine, WorkoutLog # ✅ WorkoutLog 추가
from diet.models import Meal
# ✅ 업적 모델과 프로필 모델 임포트
from achievements.models import UserAchievement 
from accounts.models import Profile

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
        profile = user.profile
        
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
        # ✅ profile 모델의 최신 정보 사용
        context_parts.append(f"- **신체 정보**: {profile.height}cm, {profile.current_weight}kg{bmi_info}")
        context_parts.append(f"- **체성분**: 골격근량 {profile.skeletal_muscle_mass or '미입력'}kg, 체지방량 {profile.body_fat_mass or '미입력'}kg")
        context_parts.append(f"- **운동 목표**: {fp.goal} (목표 체중: {profile.target_weight or '미설정'}kg)")
        context_parts.append(f"- **운동 경력/빈도**: {fp.experience}, 주 {fp.frequency}회")
        context_parts.append(f"- **선호 운동 타입**: {fp.types.replace(',', ', ')}")
        
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


    # --- 3. 최근 운동 '완료' 기록 요약 (WorkoutLog) ---
    # ⚠️ Routine(계획)이 아닌 WorkoutLog(실행 기록) 기준으로 변경
    context_parts.append("\n**[3. 최근 7일간 운동 완료 기록]**")
    try:
        recent_logs = WorkoutLog.objects.filter(
            user=user,
            completed_at__gte=datetime.now() - timedelta(days=7)
        ).select_related('routine').order_by('-completed_at')

        if recent_logs.exists():
            for log in recent_logs:
                # 운동 기록에 연결된 루틴이 있으면 루틴 이름, 없으면 "직접 운동" 등으로 표시
                log_title = log.routine.name if log.routine else "직접 기록한 운동"
                context_parts.append(f"- **{log.completed_at.strftime('%y-%m-%d')}**: {log_title} 완료")
        else:
            context_parts.append("- 기록 없음")
    except Exception as e:
        print(f"운동 완료 기록 조회 오류: {e}")
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
    
    # ✅ 5. 달성한 업적 정보 (UserAchievement) - ✨ 신규 추가 ✨
    context_parts.append("\n**[5. 주요 달성 업적 및 칭호]**")
    try:
        # 사용자가 설정한 대표 칭호
        active_title_str = "없음"
        if user.profile.active_title:
             # ForeignKey로 변경했을 경우의 코드
            active_title_str = user.profile.active_title.achievement.title_reward
        
        context_parts.append(f"- **대표 칭호**: {active_title_str}")

        # 최근에 달성한 업적 5개
        recent_achievements = UserAchievement.objects.filter(user=user).select_related('achievement').order_by('-awarded_at')[:5]
        
        if recent_achievements.exists():
            ach_list = [f"'{ach.achievement.name}'" for ach in recent_achievements]
            context_parts.append(f"- **최근 달성 업적**: {', '.join(ach_list)}")
        else:
            context_parts.append("- **최근 달성 업적**: 아직 달성한 업적이 없습니다.")
            
    except Exception as e:
        print(f"업적 정보 조회 오류: {e}")
        context_parts.append("- (업적 정보 조회 중 오류 발생)")
        
    return "\n".join(context_parts)