# routine/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpRequest
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from openai import OpenAI
from .models import Exercise, Routine, RoutineExercise
import json
import re
import requests # requests 임포트

# 1. 메인 루틴 선택 페이지
@login_required
def routine_select_view(request):
    """'AI 추천' 또는 '직접 구성'을 선택하는 메인 페이지를 렌더링합니다."""
    context = {'active_menu': 'routine'}
    return render(request, 'routine/routine_select.html', context)

# 2. GPT 기반 추천 루틴 결과 페이지
@login_required
def gpt_plan_view(request):
    """GPT에게 상세 정보(설명/주의사항 포함)를 받아 DB에 저장합니다."""
    level = request.GET.get('level', '초급')
    part = request.GET.get('part', '하체')
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # ⭐️ 1. 상세 정보를 요청하는 프롬프트로 변경
    prompt = f"""
    # 페르소나 및 역할 설정
    너는 15년 경력의 재활의학 전문 지식을 갖춘 엘리트 퍼스널 트레이너, 'Jay'다. 당신의 목표는 단순한 루틴 제공이 아니라, 사용자가 각 운동의 원리를 깊이 이해하고, 부상 위험 없이 최대의 효과를 얻도록 만드는 것이다. 모든 설명은 과학적 근거와 실전 경험을 바탕으로, 매우 구체적이고 전문적으로 작성해야 한다.

    # 사용자 정보
    - 운동 부위: '{part}'
    - 운동 수준: '{level}'

    # 루틴 생성 지침
    '{part}' 부위를 효과적으로 단련할 수 있는 운동 5개를 아래의 수준별 전략에 따라 구성하라.
    - **초급**: 부상 위험이 적은 머신 위주로 구성. 정확한 자세 인지와 목표 근육의 자극을 느끼는 데 집중.
    - **중급**: 복합 관절 운동(프리웨이트) 비중을 높여 전반적인 근력과 근비대를 동시에 추구.
    - **고급**: 고강도 훈련을 위한 운동 조합(슈퍼세트, 드롭세트 등 고려 가능)과 약점 부위를 보완할 수 있는 고립 운동을 포함.

    # 출력 형식 (매우 중요!)
    각 운동은 반드시 아래 형식을 한 줄에 맞춰, '::' 구분자를 사용하여 출력해야 한다. 총 5줄을 생성하며, 다른 어떤 텍스트도 추가하지 마라.
    "운동이름::세트::반복횟수::추_천무게(kg)::상세 설명 및 꿀팁::핵심 주의사항"

    ---
    ## 각 항목별 상세 작성 가이드라인

    ### 1. 상세 설명 및 꿀팁 (description)
    이 항목은 최소 3문장 이상으로, 아래 내용을 포함하여 매우 상세하게 작성하라.
    - **주동근 및 협력근**: 이 운동이 주로 사용하는 '주동근'과 보조적으로 사용되는 '협력근'을 해부학적 명칭을 섞어 명확히 언급하라.
    - **동작의 단계별 묘사 (Phase)**:
        - **신장성 수축 (이완 단계)**: "무게를 버티며 천천히 내려갈 때..." 와 같이, 근육이 늘어나는 단계의 핵심 자세와 속도를 구체적으로 묘사하라.
        - **단축성 수축 (수축 단계)**: "폭발적으로 밀어 올릴 때..." 와 같이, 근육을 수축시키는 단계에서 어떤 느낌에 집중해야 하는지, 그리고 호흡은 어떻게(예: 수축 시 내쉬고, 이완 시 들이마신다) 해야 하는지 설명하라.
    - **전문가 꿀팁**: 다른 사람들이 잘 모르는, 자극을 극대화할 수 있는 실전 팁을 한 가지 이상 포함하라. (예: "그립의 너비", "발의 위치", "시선 처리" 등)

    ### 2. 핵심 주의사항 (precautions)
    이 항목은 최소 3문장 이상으로, 부상 방지에 초점을 맞춰 매우 구체적으로 작성하라.
    - **가장 흔한 실수**: 초보자나 중급자들이 가장 흔하게 저지르는 잘못된 자세 1~2가지를 구체적으로 지적하라. (예: "허리의 과도한 아치", "어깨의 거상", "무릎의 내전(안으로 모임)")
    - **부상 메커니즘**: 해당 실수가 왜 위험한지, 어떤 관절이나 인대(예: "어깨 회전근개", "요추 디스크", "무릎 십자인대")에 어떤 종류의 스트레스를 주는지 간략하게 설명하라.
    - **결정적 해결책**: 이를 방지하기 위한 가장 확실하고 실용적인 해결책을 제시하라. (예: "복부와 엉덩이에 힘을 주어 코어를 단단히 잠그세요", "견갑골을 항상 후인하강 상태로 유지하세요")

    ---
    # 최종 출력 예시
    벤치프레스::4::10::60::주동근인 대흉근과 협력근인 전면 삼각근, 삼두근을 단련하는 대표적인 운동입니다. 바를 가슴 중앙까지 천천히 내리며(신장성 수축) 가슴 근육이 최대로 늘어나는 것을 느끼고, 숨을 내쉬며 폭발적으로 밀어 올리세요(단축성 수축). 이때, 그립을 조금 더 넓게 잡으면 가슴 바깥쪽의 자극을 극대화할 수 있습니다.::가장 흔한 실수는 손목이 뒤로 꺾이는 것과 허리를 과도하게 아치형으로 만드는 것입니다. 손목이 꺾이면 손목 터널 증후군을 유발할 수 있으며, 과도한 아치는 허리 디스크에 큰 부담을 줍니다. 이를 방지하려면 항상 손목을 수직으로 세우고, 복부에 힘을 주어 등이 벤치에서 과하게 뜨지 않도록 유지하는 것이 핵심입니다.
    """
    routine_details = []
    try:
        response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        content = response.choices[0].message.content
        gpt_lines = [line.strip() for line in content.split('\n') if line.strip()]

        new_routine = Routine.objects.create(user=request.user, name=f"AI 추천 루틴: {part} ({level})")

        for line in gpt_lines:
            parts = line.split('::')
            if len(parts) == 6:
                name, sets, reps, weight, description, precautions = parts
                exercise = Exercise.objects.filter(name__icontains=name.strip()).first()
                if exercise:
                    # ⭐️ 2. RoutineExercise 저장 시 설명과 주의사항도 함께 DB에 저장
                    RoutineExercise.objects.create(
                        routine=new_routine,
                        exercise=exercise,
                        sets=int(sets.strip()),
                        reps=int(reps.strip()),
                        weight=int(re.sub(r'[^0-9]', '', weight) or 0),
                        description=description.strip(),
                        precautions=precautions.strip()
                    )
                    # 프론트엔드용 데이터 (이 페이지에서는 이미 생성했으므로 바로 사용)
                    routine_details.append({
                        'name': exercise.name, 'muscle_group': exercise.muscle_group, 'gif_url': exercise.gif_url,
                        'sets': sets.strip(), 'reps': reps.strip(), 'weight': re.sub(r'[^0-9]', '', weight) or 0,
                        'exercise_type': exercise.exercise_type, 'description': description.strip(), 'precautions': precautions.strip()
                    })
    except Exception as e:
        print(f"GPT Plan View Error: {e}")
    
    context = {
        'routine_title': f"AI 추천: {part} ({level}) 루틴",
        'routine': routine_details, 'active_menu': 'routine'
    }
    return render(request, 'routine/routine_plan_with_details.html', context)

# 3. 사용자가 직접 구성한 루틴 생성 및 결과 페이지
@login_required
def custom_plan_view(request):
    """사용자가 직접 입력한 정보로 루틴을 생성하고 저장합니다."""
    exercises_json = request.GET.get('exercises', '[]')
    try:
        exercise_list = json.loads(exercises_json)
    except json.JSONDecodeError:
        return redirect('routine:select')

    if not exercise_list: return redirect('routine:select')
    
    new_routine = Routine.objects.create(user=request.user, name=f"{request.user.username}님의 맞춤 루틴")
    
    routine_details = []
    for item in exercise_list:
        exercise = Exercise.objects.filter(name=item['name']).first()
        if exercise:
            if exercise.exercise_type == 'cardio':
                duration = int(item.get('duration', 0))
                RoutineExercise.objects.create(
                    routine=new_routine, exercise=exercise, duration_minutes=int(item.get('duration', 0)),
                    description=exercise.description, precautions=exercise.precautions
                )
                routine_details.append({'name': exercise.name, 'muscle_group': exercise.muscle_group, 'gif_url': exercise.gif_url, 'duration': duration, 'exercise_type': 'cardio','description': exercise.description, 'precautions': exercise.precautions,})
            else:
                sets_val, reps_val, weight_val = int(item.get('sets', 0)), int(item.get('reps', 0)), int(item.get('weight', 0))
                RoutineExercise.objects.create(
                    routine=new_routine, exercise=exercise, sets=int(item.get('sets', 0)),
                    reps=int(item.get('reps', 0)), weight=int(item.get('weight', 0)),
                    description=exercise.description, precautions=exercise.precautions
                )
                routine_details.append({'name': exercise.name, 'muscle_group': exercise.muscle_group, 'gif_url': exercise.gif_url, 'sets': sets_val, 'reps': reps_val, 'weight': weight_val, 'exercise_type': 'strength', 'description': exercise.description, 'precautions': exercise.precautions,})

    context = {'routine_title': "내가 만든 루틴", 'routine': routine_details, 'active_menu': 'routine'}
    return render(request, 'routine/routine_plan_with_details.html', context)

# 4. 내 루틴 목록 페이지
@login_required
def my_routines_view(request):
    """현재 로그인한 사용자가 만든 모든 루틴 목록을 보여줍니다."""
    user_routines = Routine.objects.filter(user=request.user).order_by('-created_at')
    context = {'routines': user_routines, 'active_menu': 'routine_list'}
    return render(request, 'routine/my_routines.html', context)

# 5. 운동 목록 제공 API (수정됨)
def exercise_api(request):
    """특정 근육 그룹에 해당하는 운동 목록을 JSON 형태로 반환합니다."""
    group = request.GET.get('muscle_group')
    if not group:
        return JsonResponse({"error": "muscle_group 파라미터가 필요합니다."}, status=400)

    exercises = Exercise.objects.filter(exercise_type="cardio") if group == "유산소" else Exercise.objects.filter(muscle_group__icontains=group)
    
    # ⭐️ 수정: API 응답에 'exercise_type'을 추가하여 프론트엔드로 전달합니다.
    data = {
        "exercises": [
            {
                "name": ex.name,
                "muscle_group": ex.muscle_group,
                "gif_url": ex.gif_url,
                "exercise_type": ex.exercise_type  # 👈 이 부분이 추가되었습니다!
            }
            for ex in exercises
        ]
    }
    return JsonResponse(data)

# 6. 루틴 삭제 뷰
@require_POST
@login_required
def delete_routine_view(request, routine_id):
    """특정 루틴을 삭제합니다. 현재 로그인한 사용자의 소유인지 반드시 확인합니다."""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    routine.delete()
    return redirect('routine:my_routines')

# 7. 루틴 수정 페이지 뷰 (향후 확장용)
@login_required
def edit_routine_view(request, routine_id):
    """루틴 수정 페이지로 이동합니다. (현재는 목록으로 리다이렉트)"""
    routine = get_object_or_404(Routine, id=routine_id, user=request.user)
    # TODO: 추후에 수정 페이지(routine_edit.html)를 만들어 이곳에서 렌더링
    return redirect('routine:my_routines')

# routine/views.py

# ... 기존의 다른 view들 ...

def youtube_search_api(request):
    """
    쿼리를 받아 YouTube에서 동영상을 검색하고 상위 3개의 결과를 반환하는 API
    """
    query = request.GET.get('q')
    if not query:
        return JsonResponse({'error': '검색어(q)가 필요합니다.'}, status=400)

    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    if not api_key:
        return JsonResponse({'error': 'YouTube API 키가 설정되지 않았습니다.'}, status=500)

    search_url = 'https://www.googleapis.com/youtube/v3/search'
    
    params = {
        'part': 'snippet',
        'q': query,
        'key': api_key,
        'type': 'video',
        'maxResults': 4, # 썸네일 3개만 가져오기
    }

    try:
        response = requests.get(search_url, params=params)
        response.raise_for_status() # 오류가 있으면 예외 발생
        results = response.json()
        
        videos = []
        for item in results.get('items', []):
            video_data = {
                'title': item['snippet']['title'],
                'video_id': item['id']['videoId'],
                'thumbnail_url': item['snippet']['thumbnails']['medium']['url'],
            }
            videos.append(video_data)
            
        return JsonResponse({'videos': videos})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'error': '알 수 없는 오류가 발생했습니다.'}, status=500)
    