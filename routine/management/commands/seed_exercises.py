# routine/management/commands/seed_exercises.py

import time
import os
import json
from django.core.management.base import BaseCommand
from routine.models import Exercise
from django.conf import settings
import openai

# ⭐️ FIX: translate_text_with_gpt 함수를 아래 코드로 교체합니다.
def translate_text_with_gpt(text, target_lang):
    """운동 이름 또는 운동 부위를 지정된 규칙에 따라 번역합니다."""
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        language_map = {'en': 'English', 'es': 'Spanish'}
        
        # ⭐️ FIX: 운동 부위인 경우, 번역 규칙을 강화하는 프롬프트를 추가합니다.
        muscle_group_map_ko = ['하체', '가슴', '등', '어깨', '팔', '복근', '유산소', '역도', '기타']
        
        if text in muscle_group_map_ko:
            # 운동 부위 번역을 위한 특별 프롬프트
            prompt = f"""
            You are a translator for a fitness app. Your task is to translate a Korean muscle group term into a single, specific {language_map[target_lang]} term.

            # Rules:
            1.  You MUST translate the given Korean term to its corresponding term from this EXACT list:
                - Korean '하체' -> English 'Legs', Spanish 'Piernas'
                - Korean '가슴' -> English 'Chest', Spanish 'Pecho'
                - Korean '등' -> English 'Back', Spanish 'Espalda'
                - Korean '어깨' -> English 'Shoulders', Spanish 'Hombros'
                - Korean '팔' -> English 'Arms', Spanish 'Brazos'
                - Korean '복근' -> English 'Abs', Spanish 'Abdominales'
                - Korean '유산소' -> English 'Cardio', Spanish 'Cardio'
                - Korean '역도' -> English 'Weightlifting', Spanish 'Halterofilia'
                - Korean '기타' -> English 'Etc', Spanish 'Etc'
            2.  Do NOT be creative. Do NOT use synonyms. Stick to the list above.
            3.  Your output must be ONLY the single translated term. No extra text, no quotation marks.

            # Korean term to translate:
            "{text}"
            """
        else:
            # 기존의 운동 이름 번역 프롬프트
            prompt = f"Translate the following Korean exercise-related term into {language_map[target_lang]}. Provide only the single translated term as the output, without any extra text or quotation marks.\n\nKorean term: \"{text}\""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0, # 규칙을 엄격하게 따르도록 온도를 0으로 설정
            max_tokens=50
        )
        return response.choices[0].message.content.strip().replace('"', '')
    except Exception as e:
        print(f"  - 🚨 GPT 번역 오류 ({text} -> {target_lang}): {e}")
        return text # 번역 실패 시 원본 반환

# 사용자님이 제공해주신 방대한 데이터를 오타 없이 100% 반영한 최종 리스트입니다.
EXERCISE_DATA = [
    # --- 하체 ---
    {'name': '컨벤셔널 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_DL.gif'},
    {'name': '바벨 백스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_BSQT.gif'},
    {'name': '스미스머신 스플릿 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_SPLIT_SQT.gif'},
    {'name': '스미스머신 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_DL.gif'},
    {'name': '스미스머신 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_SQT.gif'},
    {'name': '덤벨 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_LUNGE.gif'},
    {'name': '덤벨 고블릿 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/GOBLET_SQT.gif'},
    {'name': '덤벨 스티프 레그 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_STIFF_DL.gif'},
    {'name': '프론트 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_FSQ.gif'},
    {'name': '저처 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ZER_SQT.gif'},
    {'name': '바벨 불가리안 스플릿 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_SPLIT_SQT.gif'},
    {'name': '덤벨 불가리안 스플릿 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_BULSPLIT_SQT.gif'},
    {'name': '덤벨 스플릿 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SPLIT_SQT.gif'},
    {'name': '맨몸 스플릿 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BW_SPLIT_SQT.gif'},
    {'name': '에어 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/AIR_SQT.gif'},
    {'name': '점프 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/JUMP_SQT.gif'},
    {'name': '케틀벨 고블릿 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_GOBLET_SQT.gif'},
    {'name': '루마니안 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/RM_BB_DL.gif'},
    {'name': '스모 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_BB_DL.gif'},
    {'name': '레그 프레스', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LEG_PRESS.gif'},
    {'name': '레그 컬', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LEG_CURL.gif'},
    {'name': '레그 익스텐션', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LGE_EXT.gif'},
    {'name': '스탠딩 카프 레이즈', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/STD_CALF_RAISE.gif'},
    {'name': '이너 싸이 머신', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INN_THIGH_MC.gif'},
    {'name': '런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LUNGE.gif'},
    {'name': '스텝업', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/STEP_UP.gif'},
    {'name': '워킹 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WLK_LUNGE.gif'},
    {'name': '덤벨 스텝업', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_STEP_UP.gif'},
    {'name': '원레그 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ONE_LEG_DL.gif'},
    {'name': '바벨 스텝업', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_STEP_UP.gif'},
    {'name': '원레그 스텝업', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ONE_LEG_STEP_UP.gif'},
    {'name': '바벨 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_LUNGE.gif'},
    {'name': '워킹 덤벨 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WLK_DB_LUNGE.gif'},
    {'name': '바벨 굿모닝', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_GOOD_MORN.gif'},
    {'name': '바벨 힙 쓰러스트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_HIP_THRUST.gif'},
    {'name': '덤벨 힙 쓰러스트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_HIP_THRUST.gif'},
    {'name': '박스 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BOX_SQT.gif'},
    {'name': '시티드 레그 컬', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_LEG_CURL.gif'},
    {'name': '라잉 레그 컬', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LYING_LEG_CURL.gif'},
    {'name': '덤벨 스모 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SM_SQT.gif'},
    {'name': '케틀벨 스모 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_SM_DL.gif'},
    {'name': '덤벨 스모 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SM_DL.gif'},
    {'name': '케틀벨 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_DL.gif'},
    {'name': '덤벨 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_DL.gif'},
    {'name': '바벨 스모 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_SM_DL.gif'},
    {'name': '원레그 레그 프레스', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ONE_LEG_PRESS.gif'},
    {'name': '사이드 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SIDE_LUNGE.gif'},
    {'name': '브이 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/V_SQT.gif'},
    {'name': '시티드 레그 프레스', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_LEG_PRESS.gif'},
    {'name': '덤벨 프론트 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_FSQ.gif'},
    {'name': '덤벨 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SQT.gif'},
    {'name': '스탠딩 레그 컬', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/STD_LEG_CURL.gif'},
    {'name': '시티드 힙 어브덕션', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_HIP_ABD.gif'},
    {'name': '스탠딩 힙 쓰러스트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/STD_HIP_THRUST.gif'},
    {'name': '머신 힙 쓰러스트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/MC_HIP_THRUST.gif'},
    {'name': '시티드 힙 쓰러스트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_HIP_THRUST.gif'},
    {'name': '바벨 워킹 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_WLK_LUNGE.gif'},
    {'name': '리버스 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_LUNGE.gif'},
    {'name': '사이드 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SIDE_SQT.gif'},
    {'name': '워킹 스텝업', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WLK_STEP_UP.gif'},
    {'name': '시티드 스텝업', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_STEP_UP.gif'},
    {'name': '시티드 원레그 스텝업', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_ONE_LEG_STEP_UP.gif'},
    {'name': '글루트 브릿지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/GLUTE_BRDG.gif'},
    {'name': '싱글 레그 글루트 브릿지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SL_GLUTE_BRDG.gif'},
    {'name': '힙 쓰러스트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HIP_THRUST.gif'},
    {'name': '리버스 브이 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_V_SQT.gif'},
    {'name': '정지 랙 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PAUSE_SQT.gif'},
    {'name': '트랩바 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/TRAP_DL.gif'},
    {'name': '헥 스쿼트 머신', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HACK_SQT.gif'},
    {'name': '정지 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PAUSE_DL.gif'},
    {'name': '정지 스모 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PAUSE_SM_DL.gif'},
    {'name': '바벨 박스 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_BOX_SQT.gif'},
    {'name': '바벨 프론트 랙 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_FR_LUNGE.gif'},
    {'name': '바벨 점프 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_JUMP_SQT.gif'},
    {'name': '바벨 란지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_LLUNGE.gif'},
    {'name': '바벨 래터럴 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_LAT_LUNGE.gif'},
    {'name': '바벨 스플릿 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_SPLIT_SQT_REAL.gif'},
    {'name': '바벨 스탠딩 카프 레이즈', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_STD_CALF_RAISE.gif'},
    {'name': '스티프 레그 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/STIFF_DL.gif'},
    {'name': '맨몸 오버헤드 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BW_OH_SQT.gif'},
    {'name': '덤벨 레그 컬', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_LEG_CURL.gif'},
    {'name': '바벨 핵 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_HACK_SQT.gif'},
    {'name': '맨몸 카프 레이즈', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BW_CALF_RAISE.gif'},
    {'name': '덤벨 루마니안 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_RM_DL.gif'},
    {'name': '라잉 힙 어브덕션', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LYING_HIP_ABD.gif'},
    {'name': '피스톨 박스 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PISTOL_BOX_SQT.gif'},
    {'name': '사이드 라잉 클램', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SIDE_LYING_CLAM.gif'},
    {'name': '맨몸 원레그 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BW_SL_DEAD.gif'},
    {'name': '바벨 원레그 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_SL_DEAD.gif'},
    {'name': '덤벨 원레그 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SL_DEAD.gif'},
    {'name': '덤벨 래터럴 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_LAT_LUNGE.gif'},
    {'name': '케틀벨 래터럴 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_LAT_LUNGE.gif'},
    {'name': '맨몸 래터럴 런지', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BW_LAT_LUNGE.gif'},
    {'name': '원레그 익스텐션', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SL_LEG_EXT.gif'},
    {'name': '원레그 컬', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SL_LEG_CURL.gif'},
    {'name': '원레그 프레스', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SL_LEG_PRESS.gif'},
    {'name': '수평 레그 프레스', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HZ_LEG_PRESS.gif'},
    {'name': '수평 원레그 프레스', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HZ_SL_LEG_PRESS.gif'},
    {'name': '시티드 원레그 컬', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_SL_LEG_CURL.gif'},
    {'name': '노르딕 햄스트링 컬', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/NOR_HAM_CURL.gif'},
    {'name': '바벨 스모 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_SM_SQT.gif'},
    {'name': '케틀벨 스모 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_SM_SQT.gif'},
    {'name': '스모 에어 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_AIR_SQT.gif'},
    {'name': '피스톨 스쿼트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PISTOL_SQT.gif'},
    {'name': '덩키 킥', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DONK_KICK.gif'},
    {'name': '케이블 덩키 킥', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_DONK_KICK.gif'},
    {'name': '데피icit 데드리프트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DEFICIT_DL.gif'},
    {'name': '런지 트위스트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LUNGE_TWIST.gif'},
    {'name': '케틀벨 런지 트위스트', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_LUNGE_TWIST.gif'},
    {'name': '케이블 풀 스루', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_PULL_THRU.gif'},
    {'name': '몬스터 글루트 머신', 'muscle_group': '하체', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/MON_GLUTE_MC.gif'},
    # --- 가슴 ---
    {'name': '벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_BP.gif'},
    {'name': '스미스머신 벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_BP.gif'},
    {'name': '스미스머신 인클라인 벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_INC_PRESS.gif'},
    {'name': '덤벨 벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_BP.gif'},
    {'name': '인클라인 덤벨 벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_INC_BP.gif'},
    {'name': '덤벨 플라이', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_FLY.gif'},
    {'name': '스탠딩 케이블 플라이', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/STD_CABLE_FLY.gif'},
    {'name': '인클라인 벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_INC_PRESS.gif'},
    {'name': '딥스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DIPS.gif'},
    {'name': '중량 딥스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WEI_DIPS.gif'},
    {'name': '인클라인 덤벨 플라이', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_INC_FLY.gif'},
    {'name': '푸시업', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PUSH_UP.gif'},
    {'name': '중량 푸시업', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WEI_PUSH_UP.gif'},
    {'name': '힌두 푸시업', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HINDU_PUSH_UP.gif'},
    {'name': '아처 푸시업', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ARCHER_PUSH_UP.gif'},
    {'name': '클로즈그립 푸시업', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CG_PUSH_UP.gif'},
    {'name': '케이블 크로스오버', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CROSS_OVER.gif'},
    {'name': '체스트 프레스 머신', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CHEST_PRESS_MC.gif'},
    {'name': '펙덱 플라이 머신', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PEC_DECK_MC.gif'},
    {'name': '인클라인 벤치프레스 머신', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INC_BP_MAC.gif'},
    {'name': '덤벨 풀오버', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_PULLOVER.gif'},
    {'name': '시티드 딥스 머신', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_DIPS_MC.gif'},
    {'name': '로우 폴리 케이블 플라이', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LP_CABLE_FLY.gif'},
    {'name': '해머 벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HAMMER_BP.gif'},
    {'name': '스포토 벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SPOTO_BP.gif'},
    {'name': '어시스트 딥스 머신', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ASS_DIP_MC.gif'},
    {'name': '디클라인 벤치프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_DEC_BP.gif'},
    {'name': '바벨 플로어 프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_FLOOR_PRESS.gif'},
    {'name': '클랩 푸시업', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CLAP_PUSH_UP.gif'},
    {'name': '디클라인 덤벨 플라이', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_DEC_FLY.gif'},
    {'name': '인클라인 푸시업', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INC_PUSH_UP.gif'},
    {'name': '파이크 푸시업', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PIKE_PUSH_UP.gif'},
    {'name': '디클라인 체스트 프레스 머신', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DEC_CHEST_MAC.gif'},
    {'name': '인클라인 덤벨 트위스트 프레스', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INC_DB_TWIST_PRESS.gif'},
    {'name': '인클라인 케이블 플라이', 'muscle_group': '가슴', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INC_CABLE_FLY.gif'},
    # --- 등 ---
    {'name': '스미스머신 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_ROW.gif'},
    {'name': '덤벨 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_LOW.gif'},
    {'name': '원암 덤벨 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/OA_DB_ROW.gif'},
    {'name': '케이블 암 풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_ARM_PULL_DOWN.gif'},
    {'name': '시티드 케이블 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEATED_CABLE_ROW.gif'},
    {'name': '굿모닝 엑서사이즈', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/GOOD_MORN.gif'},
    {'name': '풀업', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PULL_UP.gif'},
    {'name': '중량 풀업', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WEI_PULL_UP.gif'},
    {'name': '친업', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CHIN_UP.gif'},
    {'name': '중량 친업', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WEI_CHIN_UP.gif'},
    {'name': '바벨 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_LOW.gif'},
    {'name': '펜들레이 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PENDLAY_ROW.gif'},
    {'name': '인클라인 바벨 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INC_BB_ROW.gif'},
    {'name': '인클라인 덤벨 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INC_DB_ROW.gif'},
    {'name': '인버티드 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INVT_ROW.gif'},
    {'name': '바벨 풀오버', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_PULLOVER.gif'},
    {'name': '시티드 로우 머신', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/MC_LOW.gif'},
    {'name': '랫풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LAT_PULL_DOWN.gif'},
    {'name': '하이퍼 익스텐션', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HPET.gif'},
    {'name': '중량 하이퍼 익스텐션', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WEI_HPET.gif'},
    {'name': '백 익스텐션', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BACK_ET.gif'},
    {'name': '맥그립 랫풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/MAG_LAT_PULL_DOWN.gif'},
    {'name': '패러럴그립 랫풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PAR_LAT_PULL_DOWN.gif'},
    {'name': '언더그립 랫풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_LAT_PULL_DOWN.gif'},
    {'name': '정지 바벨 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PAUSE_BB_ROW.gif'},
    {'name': '어시스트 풀업 머신', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ASS_PULLUP_MC.gif'},
    {'name': '플로어 시티드 케이블 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/FLOOR_SEATED_ROW.gif'},
    {'name': '래터럴 와이드 풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LAT_WIDE_PULL.gif'},
    {'name': '언더그립 바벨 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_BB_ROW.gif'},
    {'name': '라잉 바벨 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LYING_BB_ROW.gif'},
    {'name': '비하인드 넥 풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BHD_NECK_PULL_DOWN.gif'},
    {'name': '원암 케이블 풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_OA_PULL_DOWN.gif'},
    {'name': '원암 래터럴 와이드 풀다운', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/OA_LAT_WIDE_PULL_DOWN.gif'},
    {'name': '로우 로우 머신', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LOW_ROW_MC.gif'},
    {'name': '원암 로우 로우 머신', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/OA_LOW_ROW_MC.gif'},
    {'name': '하이 로우 머신', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HIGH_ROW_MC.gif'},
    {'name': '언더그립 하이 로우 머신', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/UNDER_HIGH_ROW_MC.gif'},
    {'name': '원암 하이 로우 머신', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/OA_HIGH_ROW_MC.gif'},
    {'name': '원암 시티드 케이블 로우', 'muscle_group': '등', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/OA_CABLE_SEATED_ROW.gif'},
    # --- 어깨 ---
    {'name': '오버헤드 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_PRESS.gif'},
    {'name': '스미스머신 오버헤드 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_PRESS.gif'},
    {'name': '스미스머신 슈러그', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SM_SHRUG.gif'},
    {'name': '덤벨 숄더 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SHD_PRESS.gif'},
    {'name': '덤벨 래터럴 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_LAT_RAISE.gif'},
    {'name': '벤트오버 덤벨 래터럴 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_BO_LAT_RAISE.gif'},
    {'name': '아놀드 덤벨 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ARNOLD_DB_PRESS.gif'},
    {'name': '숄더 프레스 머신', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SHD_PRESS_MAC.gif'},
    {'name': '비하인드 넥 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_BHD_NECK_PRESS.gif'},
    {'name': '덤벨 프론트 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_F_RAISE.gif'},
    {'name': '덤벨 슈러그', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SHRUG.gif'},
    {'name': '바벨 슈러그', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_SHRUG.gif'},
    {'name': '페이스 풀', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/FACE_PULL.gif'},
    {'name': '핸드스탠드', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HS.gif'},
    {'name': '핸드스탠드 푸시업', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HSPU.gif'},
    {'name': '케이블 리버스 플라이', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_REV_FLY.gif'},
    {'name': '바벨 업라이트 로우', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_UPRIGHT_ROW.gif'},
    {'name': '덤벨 업라이트 로우', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_UPRIGHT_ROW.gif'},
    {'name': '이지바 업라이트 로우', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/EZB_UPRIGHT_ROW.gif'},
    {'name': '푸시 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PUSH_PRESS.gif'},
    {'name': '리어 델토이드 플라이 머신', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_PEC_DECK_MC.gif'},
    {'name': '래터럴 레이즈 머신', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LAT_RAISE_MC.gif'},
    {'name': '케이블 래터럴 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_LAT_RAISE.gif'},
    {'name': '케이블 프론트 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_FRONT_RAISE.gif'},
    {'name': '바벨 프론트 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_FRONT_RAISE.gif'},
    {'name': '이지바 프론트 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/EZB_FRONT_RAISE.gif'},
    {'name': '시티드 덤벨 리어 래터럴 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_REAR_LAT_RAISE.gif'},
    {'name': '숄더 탭', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SHD_TAP.gif'},
    {'name': '시티드 바벨 숄더 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_BB_SHD_PRESS.gif'},
    {'name': '시티드 덤벨 숄더 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_DB_SHD_PRESS.gif'},
    {'name': '플레이트 숄더 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PLATE_SHD_PRESS.gif'},
    {'name': 'Y 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/Y_RAISE.gif'},
    {'name': '덤벨 Y 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_Y_RAISE.gif'},
    {'name': '슈러그 머신', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SHRUG_MC.gif'},
    {'name': '케이블 슈러그', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_SHRUG.gif'},
    {'name': '케이블 인터널 로테이션', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_INT_ROT.gif'},
    {'name': '케이블 익스터널 로테이션', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_EXT_ROT.gif'},
    {'name': '원암 케이블 래터럴 레이즈', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/OA_CABLE_LAT_RAISE.gif'},
    {'name': '랜드마인 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LAND_PRESS.gif'},
    {'name': '원암 랜드마인 프레스', 'muscle_group': '어깨', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/OA_LAND_PRESS.gif'},
    # --- 팔 ---
    {'name': '덤벨 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_BC_CURL.gif'},
    {'name': '덤벨 킥백', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_KICKBACK.gif'},
    {'name': '케이블 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_CURL.gif'},
    {'name': '케이블 푸시 다운', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_PUSH_DOWN.gif'},
    {'name': '바벨 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_BC_CURL.gif'},
    {'name': '이지바 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/EZB_CURL.gif'},
    {'name': '덤벨 해머 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_HAM_CURL.gif'},
    {'name': '클로즈 그립 벤치프레스', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CG_BB_BP.gif'},
    {'name': '시티드 덤벨 트라이셉 익스텐션', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SEAT_DB_TRI_EXT.gif'},
    {'name': '케이블 트라이셉 익스텐션', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_TRI_EXT.gif'},
    {'name': '바벨 리스트 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_WRIST_CURL.gif'},
    {'name': '이지바 리스트 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/EZB_WRIST_CURL.gif'},
    {'name': '덤벨 리스트 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_WRIST_CURL.gif'},
    {'name': '스컬 크러셔', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SKULL_CRUSH.gif'},
    {'name': '바벨 라잉 트라이셉 익스텐션', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LYING_TRI_EXT.gif'},
    {'name': '덤벨 프리쳐 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_PREA_CURL.gif'},
    {'name': '바벨 프리쳐 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_PREA_CURL.gif'},
    {'name': '이지바 프리쳐 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/EZ_PREA_CURL.gif'},
    {'name': '프리쳐 컬 머신', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PREA_CURL_MAC.gif'},
    {'name': '암컬 머신', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ARM_CURL_MC.gif'},
    {'name': '케이블 해머컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_HAM_CURL.gif'},
    {'name': '케이블 오버헤드 트라이셉 익스텐션', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_OHT_EXT.gif'},
    {'name': '케이블 라잉 트라이셉 익스텐션', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_LYING_TRI_EXT.gif'},
    {'name': '리버스 바벨 리스트 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_BB_WRIST_CURL.gif'},
    {'name': '리버스 덤벨 리스트 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_DB_WRIST_CURL.gif'},
    {'name': '인클라인 덤벨 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INC_DB_CURL.gif'},
    {'name': '벤치 딥스', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BENCH_DIPS.gif'},
    {'name': '리버스 바벨 컬', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_BB_CURL.gif'},
    {'name': '트라이셉 익스텐션 머신', 'muscle_group': '팔', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/TRI_EXT_MC.gif'},
    # --- 복근 ---
    {'name': '싯업', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SIT_UP.gif'},
    {'name': '브이 업', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/V-UP.gif'},
    {'name': '크런치', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CRUNCH.gif'},
    {'name': '레그 레이즈', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/LEG_RAISE.gif'},
    {'name': '행잉 레그 레이즈', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HANG_LEG_RAIGE.gif'},
    {'name': '러시안 트위스트', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/RUS_TWIST.gif'},
    {'name': '할로우 락', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HOLLOW_ROCK.gif'},
    {'name': '할로우 포지션', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HOLLOW_POS.gif'},
    {'name': '플랭크', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PLANK.gif'},
    {'name': '덤벨 사이드 밴드', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SIDE_BEND.gif'},
    {'name': '복근 롤아웃', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ABS_ROLL_OUT.gif'},
    {'name': '복근 에어 바이크', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ABS_AIR_BIKE.gif'},
    {'name': '토즈 투 바', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/TOES_TO_BAR.gif'},
    {'name': '행잉 니 레이즈', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HANG_KNEE_RAISE.gif'},
    {'name': '복근 크런치 머신', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ABS_CRUNCH_MC.gif'},
    {'name': '필라테스 잭나이프', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/PIL_JACKKNIFE.gif'},
    {'name': '리버스 크런치', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/REV_CRUNCH.gif'},
    {'name': '사이드 플랭크', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SIDE_PLANK.gif'},
    {'name': '45도 사이드 밴드', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/45_SIDE_BEND.gif'},
    {'name': 'RKC 플랭크', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/RKC_PLANK.gif'},
    {'name': '케이블 사이드 밴드', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_CRUNCH.gif'},
    {'name': '디클라인 크런치', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DEC_CRUNCH.gif'},
    {'name': '중량 디클라인 크런치', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WEI_DEC_CRUNCH.gif'},
    {'name': '디클라인 싯업', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DEC_SIT_UP.gif'},
    {'name': '중량 디클라인 싯업', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WEI_DEC_SIT_UP.gif'},
    {'name': '사이드 크런치', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SIDE_CRUNCH.gif'},
    {'name': '케이블 트위스트', 'muscle_group': '복근', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_TWIST.gif'},
    # --- 유산소 ---
    {'name': '트레드밀', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/TREADMIL.gif'},
    {'name': '싸이클', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CYCLE.gif'},
    {'name': '로잉 머신', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ROW_MACH.gif'},
    {'name': '계단 오르기', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CLIMB_STAIRS.gif'},
    {'name': '줄넘기', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/JUMP_ROPE.gif'},
    {'name': '하이 니 스킵', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HIGH_KNEE_SKIP.gif'},
    {'name': '어썰트 바이크', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ASSAULT_BIKE.gif'},
    {'name': '스텝밀', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/STEPMILL_MAC.gif'},
    {'name': '일립티컬 머신', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/ELLIP_MC.gif'},
    {'name': '걷기', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WALKING.gif'},
    {'name': '달리기', 'muscle_group': '유산소', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/RUNNING.gif'},
    # --- 역도 ---
    {'name': '클린', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_CLEAN.gif'},
    {'name': '클린 & 저크', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_CNJ.gif'},
    {'name': '저크', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_JERK.gif'},
    {'name': '스내치', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_SNATCH.gif'},
    {'name': '바벨 오버헤드 스쿼트', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BB_OH_SQT.gif'},
    {'name': '덤벨 스내치', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_SNATCH.gif'},
    {'name': '케틀벨 스내치', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_SNATCH.gif'},
    {'name': '케이블 크런치', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CABLE_CRUNCH.gif'},
    {'name': '스내치 밸런스', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SNATCH_BAL.gif'},
    {'name': '행 클린', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HANG_CLEAN.gif'},
    {'name': '행 스내치', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/HANG_SNATCH.gif'},
    {'name': '클린 하이풀', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/CLEAN_HIGH_PULL.gif'},
    {'name': '스내치 하이풀', 'muscle_group': '역도', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SNATCH_HIGH_PULL.gif'},
    # --- 기타 ---
    {'name': '쓰러스터', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/THRUSTER.gif'},
    {'name': '버피', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BURPEE.gif'},
    {'name': '케틀벨 스윙', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_SWING.gif'},
    {'name': '파머스 워크', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/FARMER_WALK.gif'},
    {'name': '월볼 샷', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/WB_SHOT.gif'},
    {'name': '마운틴 클라이머', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/MOUNT_CLIMB.gif'},
    {'name': '박스 점프', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BOX_JUMP.gif'},
    {'name': '점핑 잭', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/JUMPING_JACK.gif'},
    {'name': '배틀링 로프', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/BAT_ROPE.gif'},
    {'name': '덤벨 버피', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_BURPEE.gif'},
    {'name': '덤벨 쓰러스터', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/DB_THRUSTER.gif'},
    {'name': '인치웜', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/INCHWORM.gif'},
    {'name': '스모 데드리프트 하이풀', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/SUMO_DEAD_HIGH.gif'},
    {'name': '케틀벨 스모 하이풀', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/KB_SUMO_HIGH.gif'},
    {'name': '터키쉬 겟업', 'muscle_group': '기타', 'gif_url': 'https://burnfit.io/wp-content/uploads/2023/11/TURKISH_GET_UP.gif'},
]


class Command(BaseCommand):
    help = 'Seeds or updates the database with exercise data, including descriptions, precautions, and translations.'

    def handle(self, *args, **options):
        start_time = time.time()
        self.stdout.write(self.style.SUCCESS('🚀 Starting to seed/update the exercise database...'))

        total_exercises = len(EXERCISE_DATA)
        for index, data in enumerate(EXERCISE_DATA):
            progress = f"({index + 1}/{total_exercises})"
            if data.get('gif_url') == 'Not Found' or not data.get('gif_url'):
                self.stdout.write(self.style.WARNING(f"{progress} Skipping '{data['name']}' (no GIF)."))
                continue

            self.stdout.write(f"\nProcessing {progress}: '{data['name']}'")

            # ⭐️ FIX: create 대신 update_or_create 사용하여 기존 데이터를 덮어쓰거나 새로 생성
            exercise, created = Exercise.objects.update_or_create(
                name=data['name'],
                defaults={
                    'muscle_group': data['muscle_group'],
                    'exercise_type': 'cardio' if data['muscle_group'] == '유산소' else 'strength',
                    'gif_url': data['gif_url'],
                }
            )

            # 번역된 이름/부위가 없을 경우에만 번역 수행
            if not exercise.name_en or not exercise.muscle_group_en:
                self.stdout.write("  - 🌐 Translating name/muscle group...")
                exercise.name_en = translate_text_with_gpt(exercise.name, 'en')
                exercise.name_es = translate_text_with_gpt(exercise.name, 'es')
                exercise.muscle_group_en = translate_text_with_gpt(exercise.muscle_group, 'en')
                exercise.muscle_group_es = translate_text_with_gpt(exercise.muscle_group, 'es')
                time.sleep(1.5) # API 과호출 방지
            else:
                self.stdout.write("  - ✅ Translations already exist. Skipping translation.")

            exercise.save() # 모든 변경사항 저장

        end_time = time.time()
        self.stdout.write(self.style.SUCCESS(f'\n✨ Seeding complete! Total time: {end_time - start_time:.2f} seconds.'))