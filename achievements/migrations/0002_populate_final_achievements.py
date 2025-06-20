# achievements/migrations/0002_populate_final_achievements.py
from django.db import migrations

# 모든 칭호 보상이 채워진 최종 업적 리스트
FINAL_ACHIEVEMENTS_LIST = [
    # EXPLORE
    {'codename': 'first_fitness_profile', 'name': '위대한 여정의 시작', 'description': '피트니스 프로필을 처음으로 작성했습니다.', 'title_reward': '새싹 헬린이', 'category': 'EXPLORE'},
    {'codename': 'first_health_survey', 'name': '나를 알다', 'description': '건강 설문을 처음으로 작성했습니다.', 'title_reward': '자기 분석가', 'category': 'EXPLORE'},
    {'codename': 'first_profile_image', 'name': '얼굴 도장 쾅!', 'description': '프로필 이미지를 처음으로 업로드했습니다.', 'title_reward': '대표 얼굴', 'category': 'EXPLORE'},
    {'codename': 'first_target_weight', 'name': '목표 설정 완료!', 'description': '목표 체중을 처음으로 설정했습니다.', 'title_reward': '계획적인', 'category': 'EXPLORE'},
    {'codename': 'first_visit', 'name': '첫 방문을 환영합니다', 'description': '회원가입 후 첫 로그인을 환영합니다.', 'title_reward': '방문객', 'category': 'EXPLORE'},
    {'codename': 'first_body_record', 'name': '내 몸 바로보기', 'description': '첫 신체 변화를 기록했습니다.', 'title_reward': '탐구하는', 'category': 'EXPLORE'},
    {'codename': 'profile_perfectionist', 'name': '프로필 완성', 'description': '나의 프로필에 있는 모든 정보를 기입했습니다.', 'title_reward': '완벽주의자', 'category': 'EXPLORE'},

    # DIET
    {'codename': 'first_meal_record', 'name': '첫 숟갈', 'description': '첫 식단을 기록했습니다.', 'title_reward': '식단 기록 초심자', 'category': 'DIET'},
    {'codename': 'first_photo_meal', 'name': '찰칵! 첫 기록', 'description': '사진으로 첫 식단을 기록했습니다.', 'title_reward': '푸드 포토그래퍼', 'category': 'DIET'},
    {'codename': 'perfect_day_meals', 'name': '완벽한 하루', 'description': '하루 세 끼 식단을 모두 기록했습니다.', 'title_reward': '꼼꼼한 기록가', 'category': 'DIET'},
    {'codename': 'meal_record_10', 'name': '식단 기록가 (브론즈)', 'description': '누적 10회 식단을 기록했습니다.', 'title_reward': '기록가', 'category': 'DIET'},
    {'codename': 'meal_record_50', 'name': '식단 기록가 (실버)', 'description': '누적 50회 식단을 기록했습니다.', 'title_reward': '숙련된 기록가', 'category': 'DIET'},
    {'codename': 'meal_record_100', 'name': '식단 기록가 (골드)', 'description': '누적 100회 식단을 기록했습니다.', 'title_reward': '기록의 장인', 'category': 'DIET'},
    {'codename': 'meal_record_365', 'name': '식단 기록가 (플래티넘)', 'description': '누적 365회 식단을 기록했습니다.', 'title_reward': '기록의 화신', 'category': 'DIET'},
    {'codename': 'protein_hunter', 'name': '단백질 사냥꾼', 'description': '한 끼에 단백질 30g 이상을 섭취했습니다.', 'title_reward': '프로틴 러버', 'category': 'DIET'},
    {'codename': 'cheating_day', 'name': '오늘은 치팅데이!', 'description': '한 끼에 1000kcal 이상을 기록했습니다.', 'title_reward': '미식가', 'category': 'DIET'},
    {'codename': 'golden_ratio_meal', 'name': '황금비율', 'description': '한 끼 식사의 영양소 비율이 황금비율에 근접했습니다.', 'title_reward': '영양학 도전자', 'category': 'DIET'},

    # WORKOUT
    {'codename': 'first_routine', 'name': '나만의 설계도', 'description': '첫 운동 루틴을 생성했습니다.', 'title_reward': '초보 설계자', 'category': 'WORKOUT'},
    {'codename': 'routine_collector_bronze', 'name': '루틴 컬렉터 (브론즈)', 'description': '누적 3개 루틴을 생성했습니다.', 'title_reward': '루틴 수집가', 'category': 'WORKOUT'},
    {'codename': 'routine_collector_silver', 'name': '루틴 컬렉터 (실버)', 'description': '누적 10개 루틴을 생성했습니다.', 'title_reward': '루틴 마스터', 'category': 'WORKOUT'},
    {'codename': 'comprehensive_routine', 'name': '종합 운동 세트', 'description': '하나의 루틴에 5개 이상의 운동을 포함시켰습니다.', 'title_reward': '운동 백화점', 'category': 'WORKOUT'},
    {'codename': 'upper_body_focus', 'name': '상체 집중', 'description': '상체 운동(가슴, 등, 어깨) 위주의 루틴을 생성했습니다.', 'title_reward': '상체 조련사', 'category': 'WORKOUT'},
    {'codename': 'lower_body_focus', 'name': '하체 집중', 'description': '하체 운동 위주의 루틴을 생성했습니다.', 'title_reward': '하체 단련가', 'category': 'WORKOUT'},
    {'codename': 'core_focus', 'name': '코어 집중', 'description': '코어/복근 운동 위주의 루틴을 생성했습니다.', 'title_reward': '코어 마스터', 'category': 'WORKOUT'},
    {'codename': 'hybrid_routine', 'name': '복합 루틴 전문가', 'description': '하나의 루틴에 근력과 유산소 운동을 모두 포함했습니다.', 'title_reward': '하이브리드 워커', 'category': 'WORKOUT'},
    {'codename': 'big_3_trainee', 'name': '삼대 오백을 향하여', 'description': '하나의 루틴에 스쿼트, 벤치프레스, 데드리프트를 모두 포함시켰습니다.', 'title_reward': '스트렝스 훈련생', 'category': 'WORKOUT'},
    {'codename': 'marathon_heart', 'name': '마라토너의 심장', 'description': '한 루틴의 총 유산소 시간이 60분을 넘었습니다.', 'title_reward': '지치지 않는 심장', 'category': 'WORKOUT'},
    {'codename': 'first_workout_done', 'name': '첫 땀방울', 'description': '첫 운동 완료를 기록했습니다.', 'title_reward': '실천가', 'category': 'WORKOUT'},
    {'codename': 'workout_log_1', 'name': '첫걸음', 'description': '누적 1회 운동을 완료했습니다.', 'title_reward': '시작이 반', 'category': 'WORKOUT'},
    {'codename': 'workout_log_5', 'name': '조금 익숙해졌나요', 'description': '누적 5회 운동을 완료했습니다.', 'title_reward': '견습생', 'category': 'WORKOUT'},
    {'codename': 'workout_log_10', 'name': '헬스장 출석도장 (브론즈)', 'description': '누적 10회 운동을 완료했습니다.', 'title_reward': '출석 도장', 'category': 'WORKOUT'},
    {'codename': 'workout_log_30', 'name': '한 달의 노력', 'description': '누적 30회 운동을 완료했습니다.', 'title_reward': '노력파', 'category': 'WORKOUT'},
    {'codename': 'workout_log_50', 'name': '헬스장 출석도장 (실버)', 'description': '누적 50회 운동을 완료했습니다.', 'title_reward': '성실한 멤버', 'category': 'WORKOUT'},
    {'codename': 'workout_log_70', 'name': '이제는 프로', 'description': '누적 70회 운동을 완료했습니다.', 'title_reward': '프로 운동러', 'category': 'WORKOUT'},
    {'codename': 'workout_log_100', 'name': '헬스장 출석도장 (골드)', 'description': '누적 100회 운동을 완료했습니다.', 'title_reward': '백전노장', 'category': 'WORKOUT'},
    {'codename': 'workout_log_300', 'name': '강철의 의지', 'description': '누적 300회 운동을 완료했습니다.', 'title_reward': '강철의 연금술사', 'category': 'WORKOUT'},
    {'codename': 'workout_log_365', 'name': '헬스장 출석도장 (마스터)', 'description': '누적 365회 운동을 완료했습니다.', 'title_reward': '헬스장 지박령', 'category': 'WORKOUT'},
    {'codename': 'target_weight_achieved', 'name': '위대한 성공', 'description': '목표 체중을 달성했습니다.', 'title_reward': '목표 분쇄기', 'category': 'WORKOUT'},
    {'codename': 'fat_loss_1kg', 'name': '가벼워진 몸', 'description': '체지방 1kg 감량에 성공했습니다.', 'title_reward': '가벼운 발걸음', 'category': 'WORKOUT'},
    {'codename': 'fat_loss_5kg', 'name': '지방 연소자', 'description': '체지방 5kg 감량에 성공했습니다.', 'title_reward': '버닝 마스터', 'category': 'WORKOUT'},
    {'codename': 'muscle_gain_1kg', 'name': '근육 성장기', 'description': '골격근량 1kg 증가에 성공했습니다.', 'title_reward': '근육 제조기', 'category': 'WORKOUT'},

    # CONSISTENCY
    {'codename': 'diet_streak_7', 'name': '주간 식단 챌린지', 'description': '7일 연속으로 식단을 기록했습니다.', 'title_reward': '성실한 기록가', 'category': 'CONSISTENCY'},
    {'codename': 'diet_streak_30', 'name': '한 달의 식단 마스터', 'description': '30일 연속으로 식단을 기록했습니다.', 'title_reward': '식단 관리의 달인', 'category': 'CONSISTENCY'},
    {'codename': 'workout_streak_3', 'name': '작심삼일 격파', 'description': '3일 연속으로 운동을 완료했습니다.', 'title_reward': '작심삼일 브레이커', 'category': 'CONSISTENCY'},
    {'codename': 'workout_streak_7', 'name': '주간 운동 챌린지', 'description': '7일 연속으로 운동을 완료했습니다.', 'title_reward': '꾸준함의 증거', 'category': 'CONSISTENCY'},
    {'codename': 'night_owl_workout', 'name': '밤샘 운동가', 'description': '모두가 잠든 밤에 운동을 완료했습니다.', 'title_reward': '밤의 지배자', 'category': 'CONSISTENCY'},
    {'codename': 'early_bird_workout', 'name': '새벽의 전사', 'description': '해가 뜨기 전 새벽에 운동을 완료했습니다.', 'title_reward': '얼리버드', 'category': 'CONSISTENCY'},
    {'codename': 'xmas_workout', 'name': '메리 헬스마스', 'description': '크리스마스에도 운동을 쉬지 않았습니다.', 'title_reward': '산타의 근육', 'category': 'CONSISTENCY'},
    {'codename': 'new_year_workout', 'name': '새해 다짐', 'description': '새해 첫날 운동으로 한 해를 시작했습니다.', 'title_reward': '결심의 실천가', 'category': 'CONSISTENCY'},
    {'codename': 'first_cardio', 'name': '심장이 뛴다', 'description': '첫 유산소 운동을 완료했습니다.', 'title_reward': '심박동', 'category': 'CONSISTENCY'},
    {'codename': 'first_strength', 'name': '근력의 맛', 'description': '첫 근력 운동을 완료했습니다.', 'title_reward': '강철의 시작', 'category': 'CONSISTENCY'},

    # CHATBOT & AI
    {'codename': 'first_ai_chat', 'name': 'AI와 첫 대화', 'description': 'AI 챗봇에게 처음으로 말을 걸었습니다.', 'title_reward': '미래와의 조우', 'category': 'CHATBOT'},
    {'codename': 'ai_advisor_bronze', 'name': 'AI 조언가', 'description': 'AI 챗봇과 누적 10회 이상 대화했습니다.', 'title_reward': 'AI 문답가', 'category': 'CHATBOT'},
    {'codename': 'ai_advisor_silver', 'name': 'AI 상담가', 'description': 'AI 챗봇과 누적 50회 이상 대화했습니다.', 'title_reward': 'AI 카운셀러', 'category': 'CHATBOT'},
    {'codename': 'ai_advisor_gold', 'name': 'AI 절친', 'description': 'AI 챗봇과 누적 150회 이상 대화했습니다.', 'title_reward': 'AI와의 교감', 'category': 'CHATBOT'},
    {'codename': 'curious_about_achievements', 'name': '궁금한 업적', 'description': 'AI에게 자신의 업적에 대해 질문했습니다.', 'title_reward': '호기심 많은', 'category': 'CHATBOT'},
    {'codename': 'creative_spark', 'name': '창의적인 불꽃', 'description': 'AI에게 이미지 생성을 요청했습니다.', 'title_reward': '디지털 아티스트', 'category': 'CHATBOT'},
    {'codename': 'data_provider', 'name': '데이터 제공자', 'description': 'AI에게 파일(이미지/문서)을 첨부하여 질문했습니다.', 'title_reward': '지식의 공유자', 'category': 'CHATBOT'},
    {'codename': 'ai_trainer', 'name': 'AI 트레이너', 'description': 'AI의 추천을 받아 운동 루틴을 생성했습니다.', 'title_reward': '스마트 트레이니', 'category': 'CHATBOT'},
    {'codename': 'ai_music_buddy', 'name': 'AI 조력자', 'description': 'AI 음악 추천 기능을 처음 사용했습니다.', 'title_reward': 'AI DJ', 'category': 'CHATBOT'},
    {'codename': 'music_curator_bronze', 'name': '음악 큐레이터 (브론즈)', 'description': '음악 추천 기능을 5회 이상 사용했습니다.', 'title_reward': 'DJ 꿈나무', 'category': 'CHATBOT'},
    {'codename': 'music_curator_silver', 'name': '음악 큐레이터 (실버)', 'description': '음악 추천 기능을 20회 이상 사용했습니다.', 'title_reward': '음악 애호가', 'category': 'CHATBOT'},
    {'codename': 'music_curator_gold', 'name': '음악 큐레이터 (골드)', 'description': '음악 추천 기능을 50회 이상 사용했습니다.', 'title_reward': '클럽 DJ', 'category': 'CHATBOT'},
    {'codename': 'music_curator_platinum', 'name': '음악 큐레이터 (플래티넘)', 'description': '음악 추천 기능을 100회 이상 사용했습니다.', 'title_reward': '사운드 마스터', 'category': 'CHATBOT'},
    {'codename': 'mood_maker', 'name': '무드 메이커', 'description': '모든 종류의 기분으로 음악을 추천받았습니다.', 'title_reward': '감정의 지배자', 'category': 'CHATBOT'},
    {'codename': 'versatile_exerciser', 'name': '만능 운동꾼', 'description': '모든 종류의 운동에 맞춰 음악을 추천받았습니다.', 'title_reward': '팔방미인', 'category': 'CHATBOT'},
    {'codename': 'meditation_time', 'name': '명상의 시간', 'description': '요가/필라테스와 차분한 음악 조합을 선택했습니다.', 'title_reward': '고요한 영혼', 'category': 'CHATBOT'},
    {'codename': 'heart_beater', 'name': '심장을 울려라', 'description': 'HIIT와 에너지 넘치는 음악 조합을 선택했습니다.', 'title_reward': '비트의 폭격기', 'category': 'CHATBOT'},

    # PLACE
    {'codename': 'place_explorer_basic', 'name': '지역 탐험가', 'description': '운동 장소 찾기 기능을 처음 사용했습니다.', 'title_reward': '첫 탐험', 'category': 'EXPLORE'},
    {'codename': 'place_search_bronze', 'name': '동네 전문가', 'description': '장소 찾기를 5회 이상 사용했습니다.', 'title_reward': '동네 지킴이', 'category': 'EXPLORE'},
    {'codename': 'place_search_silver', 'name': '도시 탐험가', 'description': '장소 찾기를 20회 이상 사용했습니다.', 'title_reward': '도시의 방랑자', 'category': 'EXPLORE'},
    {'codename': 'place_search_gold', 'name': 'GPS 마스터', 'description': '장소 찾기를 50회 이상 사용했습니다.', 'title_reward': '인간 네비게이션', 'category': 'EXPLORE'},
    {'codename': 'sports_maniac', 'name': '스포츠 매니아', 'description': '3종류 이상의 운동 장소를 검색했습니다.', 'title_reward': '스포츠 러버', 'category': 'EXPLORE'},
    {'codename': 'grand_slammer', 'name': '그랜드 슬래머', 'description': '모든 종류의 운동 장소를 검색했습니다.', 'title_reward': '만능 스포츠맨', 'category': 'EXPLORE'},
    {'codename': 'iron_path_search', 'name': '강철의 길', 'description': '헬스장을 검색했습니다.', 'title_reward': '쇠질의 길', 'category': 'EXPLORE'},
    {'codename': 'inner_peace_search', 'name': '내면의 평화', 'description': '요가/필라테스원을 검색했습니다.', 'title_reward': '평화의 탐구자', 'category': 'EXPLORE'},
    {'codename': 'aqua_adventurer_search', 'name': '아쿠아 어드벤처', 'description': '수영장을 검색했습니다.', 'title_reward': '물의 지배자', 'category': 'EXPLORE'},
    {'codename': 'ball_is_life_search', 'name': '공은 나의 친구', 'description': '구기 종목(테니스, 축구, 탁구 등) 장소를 검색했습니다.', 'title_reward': '공놀이 전문가', 'category': 'EXPLORE'},
    {'codename': 'night_planner', 'name': '밤의 계획가', 'description': '늦은 밤에 운동할 장소를 찾아봤습니다.', 'title_reward': '야행성 계획가', 'category': 'EXPLORE'},
    {'codename': 'weekend_warrior_search', 'name': '주말의 전사', 'description': '주말에 운동할 장소를 찾아봤습니다.', 'title_reward': '주말 정복자', 'category': 'EXPLORE'},
]

def populate_data(apps, schema_editor):
    Achievement = apps.get_model('achievements', 'Achievement')
    for data in FINAL_ACHIEVEMENTS_LIST:
        Achievement.objects.get_or_create(codename=data['codename'], defaults=data)

class Migration(migrations.Migration):
    dependencies = [('achievements', '0001_initial'),]
    operations = [migrations.RunPython(populate_data),]