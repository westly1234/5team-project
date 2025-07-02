import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# --- 설정: 다운로드 폴더 ---
BG_DIR = "assets/achievements/backgrounds/"
BADGE_DIR = "assets/achievements/badges/"
os.makedirs(BG_DIR, exist_ok=True)
os.makedirs(BADGE_DIR, exist_ok=True)

# --- 데이터: 관련성을 최우선으로 전수 재검증한 최종 데이터 ---
FINAL_ASSETS = {
    # EXPLORE
    'first_fitness_profile': {'bg': 'https://images.pexels.com/photos/4753928/pexels-photo-4753928.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?fitness,start', 'badge': 'https://img.icons8.com/color/96/sprout.png'},
    'first_health_survey': {'bg': 'https://images.pexels.com/photos/40568/medical-appointment-doctor-healthcare-40568.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?health,survey', 'badge': 'https://img.icons8.com/color/96/health-checkup.png'},
    'first_profile_image': {'bg': 'https://images.pexels.com/photos/1310522/pexels-photo-1310522.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?portrait,profile', 'badge': 'https://img.icons8.com/color/96/add-user-male.png'},
    'first_target_weight': {'bg': 'https://images.pexels.com/photos/863988/pexels-photo-863988.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?target,goal', 'badge': 'https://img.icons8.com/color/96/goal.png'},
    'first_visit': {'bg': 'https://images.pexels.com/photos/273722/pexels-photo-273722.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?welcome,door', 'badge': 'https://img.icons8.com/color/96/door.png'},
    'first_body_record': {'bg': 'https://images.pexels.com/photos/4386466/pexels-photo-4386466.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?body,measurement', 'badge': 'https://img.icons8.com/color/96/graph-report.png'},
    'profile_perfectionist': {'bg': 'https://images.pexels.com/photos/7129713/pexels-photo-7129713.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?perfect,checklist', 'badge': 'https://img.icons8.com/color/96/checked-user-male.png'},
    # DIET
    'first_meal_record': {'bg': 'https://images.pexels.com/photos/1640777/pexels-photo-1640777.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?healthy,food', 'badge': 'https://img.icons8.com/color/96/spoon.png'},
    'first_photo_meal': {'bg': 'https://images.pexels.com/photos/376464/pexels-photo-376464.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?food,camera', 'badge': 'https://img.icons8.com/color/96/camera.png'},
    'perfect_day_meals': {'bg': 'https://images.pexels.com/photos/1279330/pexels-photo-1279330.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?food,plate,all-day', 'badge': 'https://img.icons8.com/color/96/checked-checkbox.png'},
    'meal_record_10': {'bg': 'https://images.pexels.com/photos/5926382/pexels-photo-5926382.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?food,notebook', 'badge': 'https://img.icons8.com/color/96/bronze-medal.png'},
    'meal_record_50': {'bg': 'https://images.pexels.com/photos/262978/pexels-photo-262978.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?vegetables,meal', 'badge': 'https://img.icons8.com/color/96/silver-medal.png'},
    'meal_record_100': {'bg': 'https://images.pexels.com/photos/70497/pexels-photo-70497.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?gourmet,food', 'badge': 'https://img.icons8.com/color/96/gold-medal.png'},
    'meal_record_365': {'bg': 'https://images.pexels.com/photos/3184338/pexels-photo-3184338.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?food,calendar', 'badge': 'https://img.icons8.com/plasticine/100/diamond.png'},
    'protein_hunter': {'bg': 'https://images.pexels.com/photos/65175/pexels-photo-65175.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?steak,chicken', 'badge': 'https://img.icons8.com/color/96/steak.png'},
    'cheating_day': {'bg': 'https://images.pexels.com/photos/1633578/pexels-photo-1633578.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?burger,pizza', 'badge': 'https://img.icons8.com/color/96/pizza.png'},
    'golden_ratio_meal': {'bg': 'https://images.pexels.com/photos/1099680/pexels-photo-1099680.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?balance,diet', 'badge': 'https://img.icons8.com/color/96/scales.png'},
    # WORKOUT
    'first_routine': {'bg': 'https://images.pexels.com/photos/3183197/pexels-photo-3183197.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?workout,plan', 'badge': 'https://img.icons8.com/color/96/mind-map.png'},
    'routine_collector_bronze': {'bg': 'https://images.pexels.com/photos/207700/pexels-photo-207700.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?books,collection', 'badge': 'https://img.icons8.com/color/96/books.png'},
    'routine_collector_silver': {'bg': 'https://images.pexels.com/photos/3951901/pexels-photo-3951901.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?library,bookshelf', 'badge': 'https://img.icons8.com/color/96/book-shelf.png'},
    'comprehensive_routine': {'bg': 'https://images.pexels.com/photos/1954524/pexels-photo-1954524.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?gym,equipment', 'badge': 'https://img.icons8.com/color/96/puzzle.png'},
    'upper_body_focus': {'bg': 'https://images.pexels.com/photos/116077/pexels-photo-116077.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?push-up,bench-press', 'badge': 'https://img.icons8.com/color/96/chest.png'},
    'lower_body_focus': {'bg': 'https://images.pexels.com/photos/2261477/pexels-photo-2261477.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?squat,legs', 'badge': 'https://img.icons8.com/emoji/96/leg-emoji.png'},
    'core_focus': {'bg': 'https://images.pexels.com/photos/3775164/pexels-photo-3775164.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?abs,plank', 'badge': 'https://img.icons8.com/color/96/torso.png'},
    'hybrid_routine': {'bg': 'https://images.pexels.com/photos/3822623/pexels-photo-3822623.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?running,weight-lifting', 'badge': 'https://img.icons8.com/color/96/cycling-road.png'},
    'big_3_trainee': {'bg': 'https://images.pexels.com/photos/1552252/pexels-photo-1552252.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?powerlifting,deadlift', 'badge': 'https://img.icons8.com/color/96/deadlift.png'},
    'marathon_heart': {'bg': 'https://images.pexels.com/photos/2528323/pexels-photo-2528323.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?running,marathon', 'badge': 'https://img.icons8.com/color/96/running.png'},
    'first_workout_done': {'bg': 'https://images.pexels.com/photos/270085/pexels-photo-270085.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?sweat,workout', 'badge': 'https://img.icons8.com/color/96/sweat.png'},
    'workout_log_1': {'bg': 'https://images.pexels.com/photos/4720305/pexels-photo-4720305.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?first,step', 'badge': 'https://img.icons8.com/color/96/1-c.png'},
    'workout_log_5': {'bg': 'https://images.pexels.com/photos/4162451/pexels-photo-4162451.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?five,steps', 'badge': 'https://img.icons8.com/color/96/5-c.png'},
    'workout_log_10': {'bg': 'https://images.pexels.com/photos/3490348/pexels-photo-3490348.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?ten,times', 'badge': 'https://img.icons8.com/color/96/10-c.png'},
    'workout_log_30': {'bg': 'https://images.pexels.com/photos/3184454/pexels-photo-3184454.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?calendar,month', 'badge': 'https://img.icons8.com/color/96/30-c.png'},
    'workout_log_50': {'bg': 'https://images.pexels.com/photos/1552242/pexels-photo-1552242.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?gym,member', 'badge': 'https://img.icons8.com/color/96/50-c.png'},
    'workout_log_70': {'bg': 'https://images.pexels.com/photos/2294361/pexels-photo-2294361.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?professional,athlete', 'badge': 'https://img.icons8.com/color/96/70-c.png'},
    'workout_log_100': {'bg': 'https://images.pexels.com/photos/1229356/pexels-photo-1229356.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?veteran,strong', 'badge': 'https://img.icons8.com/color/96/100.png'},
    'workout_log_300': {'bg': 'https://images.pexels.com/photos/791763/pexels-photo-791763.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?iron,will', 'badge': 'https://img.icons8.com/color/96/300.png'},
    'workout_log_365': {'bg': 'https://images.pexels.com/photos/2247179/pexels-photo-2247179.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?gym,addict', 'badge': 'https://img.icons8.com/color-glass/96/trophy.png'},
    'target_weight_achieved': {'bg': 'https://images.pexels.com/photos/2246476/pexels-photo-2246476.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?success,celebration', 'badge': 'https://img.icons8.com/color/96/laurel-wreath.png'},
    'fat_loss_1kg': {'bg': 'https://images.pexels.com/photos/1346211/pexels-photo-1346211.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?scale,light-weight', 'badge': 'https://img.icons8.com/color/96/scale.png'},
    'fat_loss_5kg': {'bg': 'https://images.pexels.com/photos/260352/pexels-photo-260352.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?fire,burning', 'badge': 'https://img.icons8.com/color/96/fire-element.png'},
    'muscle_gain_1kg': {'bg': 'https://images.pexels.com/photos/2204196/pexels-photo-2204196.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?muscle,biceps', 'badge': 'https://img.icons8.com/color/96/super-mario.png'},
    # CONSISTENCY & HIDDEN
    'diet_streak_7': {'bg': 'https://images.pexels.com/photos/952356/pexels-photo-952356.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?week,calendar', 'badge': 'https://img.icons8.com/color/96/calendar-7.png'},
    'diet_streak_30': {'bg': 'https://images.pexels.com/photos/5966141/pexels-photo-5966141.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?month,calendar', 'badge': 'https://img.icons8.com/color/96/calendar-30.png'},
    'workout_streak_3': {'bg': 'https://images.pexels.com/photos/28080/pexels-photo.jpg', 'bg_fallback': 'https://source.unsplash.com/400x240/?keep,going', 'badge': 'https://img.icons8.com/color/96/flex-biceps.png'},
    'workout_streak_7': {'bg': 'https://images.pexels.com/photos/2261482/pexels-photo-2261482.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?consistency,effort', 'badge': 'https://img.icons8.com/color/96/ok-hand.png'},
    'night_owl_workout': {'bg': 'https://images.pexels.com/photos/1083822/pexels-photo-1083822.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?night,moon', 'badge': 'https://img.icons8.com/color/96/owl.png'},
    'early_bird_workout': {'bg': 'https://images.pexels.com/photos/326231/pexels-photo-326231.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?sunrise,morning', 'badge': 'https://img.icons8.com/color/96/sunrise.png'},
    'xmas_workout': {'bg': 'https://images.pexels.com/photos/1345091/pexels-photo-1345091.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?christmas,gym', 'badge': 'https://img.icons8.com/color/96/christmas-tree.png'},
    'new_year_workout': {'bg': 'https://images.pexels.com/photos/1797170/pexels-photo-1797170.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?new-year,fireworks', 'badge': 'https://img.icons8.com/color/96/confetti.png'},
    'first_cardio': {'bg': 'https://images.pexels.com/photos/3621104/pexels-photo-3621104.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?heartbeat,running-track', 'badge': 'https://img.icons8.com/color/96/heart-with-pulse.png'},
    'first_strength': {'bg': 'https://images.pexels.com/photos/3253501/pexels-photo-3253501.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?weight-lifting,strong', 'badge': 'https://img.icons8.com/color/96/dumbbell.png'},
    # CHATBOT, MUSIC, PLACE
    'first_ai_chat': {'bg': 'https://images.pexels.com/photos/8386440/pexels-photo-8386440.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?robot,future', 'badge': 'https://img.icons8.com/color/96/chatgpt.png'},
    'ai_advisor_bronze': {'bg': 'https://images.pexels.com/photos/3184433/pexels-photo-3184433.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?robot,talking', 'badge': 'https://img.icons8.com/color/96/communication.png'},
    'ai_advisor_silver': {'bg': 'https://images.pexels.com/photos/3184423/pexels-photo-3184423.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?robot,counseling', 'badge': 'https://img.icons8.com/color/96/idea-sharing.png'},
    'ai_advisor_gold': {'bg': 'https://images.pexels.com/photos/3184306/pexels-photo-3184306.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?robot,friend', 'badge': 'https://img.icons8.com/color/96/two-hearts.png'},
    'curious_about_achievements': {'bg': 'https://images.pexels.com/photos/1111304/pexels-photo-1111304.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?curiosity,question-mark', 'badge': 'https://img.icons8.com/color/96/faq.png'},
    'creative_spark': {'bg': 'https://images.pexels.com/photos/102127/pexels-photo-102127.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?creative,art', 'badge': 'https://img.icons8.com/color/96/paint-palette.png'},
    'data_provider': {'bg': 'https://images.pexels.com/photos/5926395/pexels-photo-5926395.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?data,upload', 'badge': 'https://img.icons8.com/color/96/upload-to-cloud.png'},
    'ai_trainer': {'bg': 'https://images.pexels.com/photos/3184405/pexels-photo-3184405.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?smart,trainer', 'badge': 'https://img.icons8.com/color/96/robot-3.png'},
    'ai_music_buddy': {'bg': 'https://images.pexels.com/photos/3783471/pexels-photo-3783471.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?ai,music', 'badge': 'https://img.icons8.com/color/96/music-robot.png'},
    'music_curator_bronze': {'bg': 'https://images.pexels.com/photos/167092/pexels-photo-167092.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?playlist,cassette', 'badge': 'https://img.icons8.com/color/96/playlist.png'},
    'music_curator_silver': {'bg': 'https://images.pexels.com/photos/96380/pexels-photo-96380.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?vinyl,record', 'badge': 'https://img.icons8.com/color/96/vinyl-record.png'},
    'music_curator_gold': {'bg': 'https://images.pexels.com/photos/1105666/pexels-photo-1105666.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?concert,club', 'badge': 'https://img.icons8.com/color/96/concert.png'},
    'music_curator_platinum': {'bg': 'https://images.pexels.com/photos/2240763/pexels-photo-2240763.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?dj,festival', 'badge': 'https://img.icons8.com/color/96/dj.png'},
    'mood_maker': {'bg': 'https://images.pexels.com/photos/3756879/pexels-photo-3756879.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?mood,emotion', 'badge': 'https://img.icons8.com/color/96/smiling-face-with-heart.png'},
    'versatile_exerciser': {'bg': 'https://images.pexels.com/photos/3183150/pexels-photo-3183150.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?versatile,multitasking', 'badge': 'https://img.icons8.com/color/96/reseller.png'},
    'meditation_time': {'bg': 'https://images.pexels.com/photos/3822725/pexels-photo-3822725.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?meditation,yoga', 'badge': 'https://img.icons8.com/color/96/relax-with-book.png'},
    'heart_beater': {'bg': 'https://images.pexels.com/photos/4046648/pexels-photo-4046648.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?heartbeat,energy', 'badge': 'https://img.icons8.com/color/96/fire-heart.png'},
    'place_explorer_basic': {'bg': 'https://images.pexels.com/photos/347141/pexels-photo-347141.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?map,explore', 'badge': 'https://img.icons8.com/color/96/map-marker.png'},
    'place_search_bronze': {'bg': 'https://images.pexels.com/photos/374052/pexels-photo-374052.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?town,street-view', 'badge': 'https://img.icons8.com/color/96/street-view.png'},
    'place_search_silver': {'bg': 'https://images.pexels.com/photos/374870/pexels-photo-374870.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?city,urban', 'badge': 'https://img.icons8.com/color/96/city.png'},
    'place_search_gold': {'bg': 'https://images.pexels.com/photos/3473569/pexels-photo-3473569.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?world,gps', 'badge': 'https://img.icons8.com/color/96/globe.png'},
    'sports_maniac': {'bg': 'https://images.pexels.com/photos/163452/basketball-dunk-blue-game-163452.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?sports,ball', 'badge': 'https://img.icons8.com/color/96/badminton.png'},
    'grand_slammer': {'bg': 'https://images.pexels.com/photos/209977/pexels-photo-209977.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?stadium,trophy', 'badge': 'https://img.icons8.com/color/96/trophy.png'},
    'iron_path_search': {'bg': 'https://images.pexels.com/photos/1552106/pexels-photo-1552106.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?gym,weights', 'badge': 'https://img.icons8.com/color/96/bench-press.png'},
    'inner_peace_search': {'bg': 'https://images.pexels.com/photos/2253634/pexels-photo-2253634.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?yoga,calm', 'badge': 'https://img.icons8.com/color/96/yoga.png'},
    'aqua_adventurer_search': {'bg': 'https://images.pexels.com/photos/863977/pexels-photo-863977.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?swimming,pool', 'badge': 'https://img.icons8.com/color/96/swimming.png'},
    'ball_is_life_search': {'bg': 'https://images.pexels.com/photos/209841/pexels-photo-209841.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?tennis,soccer', 'badge': 'https://img.icons8.com/color/96/ping-pong.png'},
    'night_planner': {'bg': 'https://images.pexels.com/photos/799443/pexels-photo-799443.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?night,plan', 'badge': 'https://img.icons8.com/color/96/planner.png'},
    'weekend_warrior_search': {'bg': 'https://images.pexels.com/photos/1119794/pexels-photo-1119794.jpeg', 'bg_fallback': 'https://source.unsplash.com/400x240/?weekend,adventure', 'badge': 'https://img.icons8.com/color/96/knight.png'},
}

def _download_url_with_retry(url, path, max_retries=3):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            with open(path, 'wb') as f:
                f.write(response.content)
            time.sleep(0.1)
            return True, None
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"  > 시도 {attempt + 1} 실패: {os.path.basename(path)} ({e.__class__.__name__})... 1초 후 재시도")
                time.sleep(1)
            else:
                return False, e

def download_asset(codename, urls):
    # --- 뱃지 다운로드 ---
    badge_path = os.path.join(BADGE_DIR, f"{codename}.png")
    badge_success, badge_error = _download_url_with_retry(urls['badge'], badge_path)
    if badge_success:
        print(f"  성공 (뱃지): {codename}.png")
    else:
        print(f"  최종 실패 (뱃지): {codename}.png - {badge_error}")

    # --- 배경 다운로드 (예비 URL 포함) ---
    bg_path = os.path.join(BG_DIR, f"{codename}.jpg")
    bg_success, bg_error = _download_url_with_retry(urls['bg'], bg_path)
    if not bg_success:
        print(f"  > 기본 배경 실패 ({bg_error}), 예비 URL로 전환: {codename}.jpg")
        fallback_success, fallback_error = _download_url_with_retry(urls['bg_fallback'], bg_path)
        if fallback_success:
            print(f"  성공 (예비 배경): {codename}.jpg")
        else:
            print(f"  최종 실패 (예비 배경): {codename}.jpg - {fallback_error}")
    else:
        print(f"  성공 (배경): {codename}.jpg")

# --- 메인 실행 로직 ---
print("--- 모든 자산 다운로드를 시작합니다 (V12 - 최종 수정 및 소스 교체) ---")
with ThreadPoolExecutor(max_workers=5) as executor:
    tasks = [executor.submit(download_asset, codename, urls) for codename, urls in FINAL_ASSETS.items()]
    for future in as_completed(tasks):
        try:
            future.result()
        except Exception as e:
            print(f"  작업 실행 중 오류 발생: {e}")
print("--- 모든 자산 다운로드 완료 ---")