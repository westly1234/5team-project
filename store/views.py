from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.conf import settings
from django.core.files.base import ContentFile
from .models import (
    Brand, Tag, Review, BrandCategory, Product, 
    BodyShapeAnalysis, ClothingRecommendation
)
import json
import os
import openai
import traceback
from PIL import Image
from io import BytesIO

# ==========================================================
#  페이지 렌더링 뷰
# ==========================================================

def store_home_view(request):
    """스토어 메인 페이지를 렌더링합니다."""
    brands_queryset = Brand.objects.all().prefetch_related('categories', 'tags')
    favorite_brand_ids = request.user.favorite_brands.values_list('id', flat=True) if request.user.is_authenticated else []

    category_code = request.GET.get('category')
    starts_with = request.GET.get('starts_with')
    query = request.GET.get('q')
    
    current_filter_params_dict = request.GET.copy()
    if 'page' in current_filter_params_dict:
        del current_filter_params_dict['page']
    current_filter_params = '&' + current_filter_params_dict.urlencode() if current_filter_params_dict else ''

    if category_code:
        brands_queryset = brands_queryset.filter(categories__code=category_code)
    if starts_with:
        if starts_with == '0-9': brands_queryset = brands_queryset.filter(name__iregex=r'^[0-9]')
        else: brands_queryset = brands_queryset.filter(name__istartswith=starts_with)
    if query:
        brands_queryset = brands_queryset.filter(name__icontains=query)

    paginator = Paginator(brands_queryset.distinct().order_by('name'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'alphabet': list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        'categories': BrandCategory.objects.all().order_by('name'),
        'current_category': category_code,
        'current_filter': starts_with,
        'search_query': query,
        'current_filter_params': current_filter_params,
        'active_menu': 'store',
        'favorite_brand_ids': favorite_brand_ids,
    }
    return render(request, 'store/store.html', context)

@login_required
def favorite_brands_view(request):
    """현재 사용자가 찜한 브랜드 목록 페이지를 렌더링합니다."""
    favorite_brands = request.user.favorite_brands.all().prefetch_related('categories')
    favorite_brand_ids = favorite_brands.values_list('id', flat=True)
    context = {'favorite_brands': favorite_brands, 'favorite_brand_ids': favorite_brand_ids, 'active_menu': 'store'}
    return render(request, 'store/my_favorites.html', context)

def brand_finder_view(request):
    """브랜드 찾기(퀴즈) 페이지를 렌더링하고 결과를 처리합니다."""
    if request.method == 'POST':
        goal = request.POST.get('goal')
        priority = request.POST.get('priority')
        category_code = request.POST.get('category')
        results = Brand.objects.all()

        if goal == 'diet': results = results.filter(tags__name__in=['다이어트', '저칼로리', '체지방감소'])
        elif goal == 'muscle': results = results.filter(tags__name__in=['단백질', '근성장', 'WPI', '부스터'])
        if priority == 'vegan': results = results.filter(tags__name__in=['비건', '자연주의'])
        elif priority == 'cost': results = results.filter(tags__name__in=['가성비'])
        if category_code and category_code != 'ALL': 
            results = results.filter(categories__code=category_code)
        
        context = {
            'results': results.distinct().annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')[:5],
            'is_result': True,
            'active_menu': 'store',
        }
        return render(request, 'store/brand_finder.html', context)

    context = {'categories': BrandCategory.objects.all().order_by('name'), 'is_result': False, 'active_menu': 'store'}
    return render(request, 'store/brand_finder.html', context)

def compare_page_view(request):
    """브랜드 비교 결과 페이지를 렌더링합니다."""
    context = {'ids': request.GET.get('ids', ''), 'active_menu': 'store'}
    return render(request, 'store/compare_page.html', context)

@login_required
def body_shape_analyzer_view(request):
    """체형 분석 페이지를 렌더링합니다."""
    return render(request, 'store/body_shape_analyzer.html')


# ==========================================================
#  API (Application Programming Interface) 뷰
# ==========================================================

def brand_detail_api(request, brand_id):
    """브랜드 상세 정보를 JSON으로 반환하고, 설명이 없으면 AI로 생성합니다."""
    try:
        brand = Brand.objects.get(pk=brand_id)
        if not brand.detailed_description:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    categories_str = ", ".join([cat.name for cat in brand.categories.all()])
                    tags_str = ", ".join([tag.name for tag in brand.tags.all()])
                    prompt_text = f"헬스/피트니스 브랜드 '{brand.name}'에 대한 간결하고 매력적인 한국어 소개글을 3~4문장으로 작성해줘.\n주요 정보:\n- 카테고리: {categories_str or '정보 없음'}\n- 핵심 태그: {tags_str or '정보 없음'}\n결과는 다른 부연 설명 없이, 생성된 소개글 텍스트만 깔끔하게 출력해줘."
                    client = openai.OpenAI(api_key=api_key)
                    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_text}], temperature=0.7, max_tokens=300)
                    brand.detailed_description = response.choices[0].message.content.strip()
                    brand.save(update_fields=['detailed_description'])
                except Exception as e:
                    print(f"OpenAI API 호출 중 오류 발생: {e}")
            else:
                print("OPENAI_API_KEY가 설정되지 않았습니다.")

        reviews_agg = brand.reviews.aggregate(avg_rating=Avg('rating'), review_count=Count('id'))
        reviews = brand.reviews.select_related('user').order_by('-created_at')[:10]
        reviews_data = [{'user_username': r.user.username, 'rating': r.rating, 'content': r.content, 'created_at': r.created_at.strftime('%Y-%m-%d')} for r in reviews]
        user_review_data = None
        if request.user.is_authenticated:
            user_review = Review.objects.filter(brand=brand, user=request.user).first()
            if user_review: user_review_data = {'rating': user_review.rating, 'content': user_review.content}
        
        data = {
            'id': brand.id, 'name': brand.name, 'link': brand.link, 'thumbnail_url': brand.thumbnail.url if brand.thumbnail else None,
            'detailed_description': brand.detailed_description or "상세 설명이 아직 없습니다.",
            'avg_rating': reviews_agg['avg_rating'] or 0, 'review_count': reviews_agg['review_count'] or 0,
            'reviews': reviews_data, 'user_review': user_review_data, 'is_authenticated': request.user.is_authenticated,
        }
        return JsonResponse(data)
    except Brand.DoesNotExist:
        return JsonResponse({'error': 'Brand not found'}, status=404)

@login_required
def toggle_favorite_api(request, brand_id):
    """찜하기/취소 기능을 처리합니다."""
    if request.method == 'POST':
        brand = get_object_or_404(Brand, pk=brand_id)
        if brand in request.user.favorite_brands.all():
            request.user.favorite_brands.remove(brand)
            favorited = False
        else:
            request.user.favorite_brands.add(brand)
            favorited = True
        return JsonResponse({'status': 'ok', 'favorited': favorited})
    return HttpResponseBadRequest("Invalid request method.")

@login_required
def add_review_api(request, brand_id):
    """리뷰 추가/수정을 처리합니다."""
    if request.method == 'POST':
        brand = get_object_or_404(Brand, pk=brand_id)
        data = json.loads(request.body)
        rating, content = data.get('rating'), data.get('content')
        if not rating or not content:
            return JsonResponse({'status': 'error', 'message': '평점과 내용을 모두 입력해주세요.'}, status=400)
        review, created = Review.objects.update_or_create(brand=brand, user=request.user, defaults={'rating': rating, 'content': content})
        message = '리뷰가 성공적으로 등록되었습니다.' if created else '리뷰가 성공적으로 수정되었습니다.'
        return JsonResponse({'status': 'ok', 'message': message})
    return HttpResponseBadRequest("Invalid request method.")

def compare_brands_api(request):
    """브랜드 비교를 위한 데이터를 JSON으로 반환하고, 태그가 없으면 AI로 생성합니다."""
    ids_str = request.GET.get('ids')
    if not ids_str: return JsonResponse({'error': 'No brand IDs provided'}, status=400)
    ids = [int(id) for id in ids_str.split(',') if id.isdigit()]
    brands = Brand.objects.filter(pk__in=ids).annotate(avg_rating=Avg('reviews__rating')).prefetch_related('tags', 'categories')
    brands_data = []
    for brand in brands:
        if not brand.tags.exists() and brand.detailed_description:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    prompt_text = f"다음 텍스트에서 이 브랜드를 가장 잘 나타내는 핵심 키워드를 3~4개만 쉼표(,)로 구분해서 한국어로 추출해줘.\n다른 부연 설명은 전혀 붙이지 말고, 오직 키워드만 '키워드1,키워드2,키워드3' 형식으로 응답해줘.\n---\n텍스트: \"{brand.detailed_description}\"\n---"
                    client = openai.OpenAI(api_key=api_key)
                    response = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt_text}], temperature=0.3, max_tokens=50)
                    keywords = [kw.strip() for kw in response.choices[0].message.content.strip().split(',') if kw.strip()]
                    for keyword_name in keywords:
                        tag, created = Tag.objects.get_or_create(name=keyword_name)
                        brand.tags.add(tag)
                except Exception as e:
                    print(f"OpenAI API 호출 중 오류(태그 생성): {e}")
            else:
                print("OPENAI_API_KEY가 설정되지 않아 태그를 생성할 수 없습니다.")
        
        brands_data.append({
            'id': brand.id, 'name': brand.name, 'thumbnail_url': brand.thumbnail.url if brand.thumbnail else None,
            'categories': [cat.name for cat in brand.categories.all()], 'link': brand.link,
            'avg_rating': brand.avg_rating or 0, 'promotion_info': brand.promotion_info,
            'tags': [tag.name for tag in brand.tags.all()]
        })
    return JsonResponse({'brands': brands_data})

def filter_brands_api(request):
    """AJAX 요청에 따라 필터링된 브랜드 목록과 페이지네이션 HTML을 반환합니다."""
    brands_queryset = Brand.objects.all().prefetch_related('categories', 'tags')
    favorite_brand_ids = request.user.favorite_brands.values_list('id', flat=True) if request.user.is_authenticated else []
    category_code = request.GET.get('category')
    starts_with = request.GET.get('starts_with')
    query = request.GET.get('q')
    current_filter_params_dict = request.GET.copy()
    if 'page' in current_filter_params_dict: del current_filter_params_dict['page']
    current_filter_params = '&' + current_filter_params_dict.urlencode() if current_filter_params_dict else ''
    if category_code: brands_queryset = brands_queryset.filter(categories__code=category_code)
    if starts_with:
        if starts_with == '0-9': brands_queryset = brands_queryset.filter(name__iregex=r'^[0-9]')
        else: brands_queryset = brands_queryset.filter(name__istartswith=starts_with)
    if query: brands_queryset = brands_queryset.filter(name__icontains=query)
    paginator = Paginator(brands_queryset.distinct().order_by('name'), 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj, 'favorite_brand_ids': favorite_brand_ids, 'search_query': query, 'current_filter_params': current_filter_params}
    brands_html = render_to_string('store/partials/brand_grid.html', context, request=request)
    return JsonResponse({'brands_html': brands_html})


# ==========================================================
#  체형 분석 기능 (전문가 수준 업그레이드)
# ==========================================================

def analyze_image_for_body_shape(image_path, output_skeleton_path):
    """
    이미지의 기하학적 비율과 스켈레톤만 분석하여 반환합니다.
    """
    try:
        import cv2
        import mediapipe as mp
        import numpy as np
    except ImportError:
        return None, None, "서버에 분석 라이브러리(OpenCV, MediaPipe)가 설치되지 않았습니다."

    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils

    with mp_pose.Pose(static_image_mode=True, model_complexity=2, min_detection_confidence=0.5) as pose:
        image = cv2.imread(str(image_path))
        if image is None: return None, None, "이미지 파일을 읽을 수 없습니다."
        
        annotated_image = image.copy()
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if not results.pose_landmarks: return None, None, "사진에서 신체를 감지하지 못했습니다."

        mp_drawing.draw_landmarks(
            annotated_image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=mp_drawing.DrawingSpec(color=(255, 255, 255, 128), thickness=2),
            connection_drawing_spec=mp_drawing.DrawingSpec(color=(78, 205, 196), thickness=2)
        )
        cv2.imwrite(str(output_skeleton_path), annotated_image)

        landmarks = results.pose_landmarks.landmark
        
        p_shoulder_l = np.array([landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y])
        p_shoulder_r = np.array([landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y])
        p_hip_l = np.array([landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y])
        p_hip_r = np.array([landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y])
        p_waist_l_est = (p_shoulder_l + p_hip_l * 1.5) / 2.5
        p_waist_r_est = (p_shoulder_r + p_hip_r * 1.5) / 2.5
        
        shoulder_width = np.linalg.norm(p_shoulder_l - p_shoulder_r)
        hip_width = np.linalg.norm(p_hip_l - p_hip_r)
        waist_width = np.linalg.norm(p_waist_l_est - p_waist_r_est)
        
        shoulder_to_hip_ratio = shoulder_width / hip_width if hip_width > 0 else 1
        waist_to_hip_ratio = waist_width / hip_width if hip_width > 0 else 1

        body_shape = 'OVAL'
        if shoulder_to_hip_ratio > 1.05: body_shape = 'INVERTED_TRIANGLE'
        elif shoulder_to_hip_ratio < 0.95: body_shape = 'TRIANGLE'
        else:
            if waist_to_hip_ratio < 0.8: body_shape = 'HOURGLASS'
            else: body_shape = 'RECTANGLE'

        geometric_data = {
            'body_shape': body_shape,
            'shoulder_to_hip_ratio': shoulder_to_hip_ratio,
        }
        return body_shape, geometric_data, "분석 성공"

@login_required
def analyze_body_shape_api(request):
    """프로필 정보(BMI)와 이미지 분석(기하학)을 결합하여 초개인화된 AI 스타일링 팁을 생성합니다."""
    if request.method != 'POST' or not request.FILES.get('image'):
        return JsonResponse({'status': 'error', 'message': '잘못된 요청입니다.'}, status=400)
    
    # 1. 사용자의 프로필 정보 및 BMI 계산
    try:
        profile = request.user.profile
        if not profile.height or not profile.current_weight:
            return JsonResponse({'status': 'error', 'message': '체형 분석을 위해 프로필에 키와 현재 체중을 먼저 입력해주세요.'}, status=400)
        
        height_m = profile.height / 100
        bmi = profile.current_weight / (height_m ** 2)
        
        physique = "표준 체형"
        if bmi < 18.5: physique = "마른 체형"
        elif bmi >= 25 and bmi < 30: physique = "과체중"
        elif bmi >= 30: physique = "비만 체형"
        
    except Exception: # Profile.DoesNotExist 포함
        return JsonResponse({'status': 'error', 'message': '프로필 정보를 찾을 수 없습니다.'}, status=404)

    # 2. 프론트엔드에서 전송된 성별 값 받기
    gender = request.POST.get('gender')
    if not gender in ['male', 'female']:
        return JsonResponse({'status': 'error', 'message': '성별을 선택해주세요.'}, status=400)
    
    user_concerns = request.POST.get('concerns', '').strip()

    # 3. 이미지 유효성 검사 및 처리
    image_file = request.FILES['image']
    if image_file.size > 10 * 1024 * 1024: # 10MB
        return JsonResponse({'status': 'error', 'message': '이미지 파일은 10MB를 초과할 수 없습니다.'})

    try:
        img = Image.open(image_file)
        img.verify()
        image_file.seek(0)
        img = Image.open(image_file)
        if img.width > 1024 or img.height > 1024: img.thumbnail((1024, 1024))
        
        output = BytesIO()
        img.convert('RGB').save(output, format='JPEG', quality=85)
        output.seek(0)
        
        image_file_to_save = ContentFile(output.read(), name=f"{request.user.id}_{os.path.splitext(image_file.name)[0]}.jpg")
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'유효하지 않은 이미지 파일입니다: {e}'})

    # 4. 분석 기록 인스턴스 생성 및 원본 이미지 저장
    analysis_instance = BodyShapeAnalysis(user=request.user)
    analysis_instance.source_image.save(image_file_to_save.name, image_file_to_save, save=True)
    
    # 5. 스켈레톤 이미지 저장 경로 설정
    skeleton_image_name = f"skeleton_{os.path.basename(analysis_instance.source_image.name)}"
    skeleton_folder = os.path.join(settings.MEDIA_ROOT, 'body_analysis', 'skeleton')
    os.makedirs(skeleton_folder, exist_ok=True)
    skeleton_image_path = os.path.join(skeleton_folder, skeleton_image_name)

    try:
        # 6. 기하학적 분석 실행
        body_shape, geometric_data, message = analyze_image_for_body_shape(
            analysis_instance.source_image.path, 
            skeleton_image_path
        )
        
        if body_shape:
            # 7. OpenAI API 호출
            api_key = os.getenv("OPENAI_API_KEY")
            ai_recommendations = "추천 스타일 생성 중 오류가 발생했습니다."
            ai_style_tips = "스타일링 팁 생성 중 오류가 발생했습니다."

            if api_key:
                try:
                    gender_kor = "남성" if gender == "male" else "여성"
                    shape_kor = dict(BodyShapeAnalysis.body_shape_choices).get(body_shape, "분석 불가")

                    prompt = f"""
                    당신은 데이터 기반으로 스타일을 분석하는 현실주의 패션 전략가입니다.
                    당신의 목표는 예쁘게 꾸며주는 게 아니라, **이 고객의 체형이 사회적으로 가장 무난하게 보이도록 설계하는 것**입니다.

                    [고객 데이터]
                    - 성별: {gender_kor}
                    - 키: {profile.height} cm
                    - 몸무게: {profile.current_weight} kg
                    - 체구(BMI): {physique} (BMI: {bmi:.1f})
                    - 골격 형태: {shape_kor}
                    - 사용자 개인 고민: "{user_concerns if user_concerns else "특별한 고민 없음"}"

                    [지시사항]
                    1. '사용자 개인 고민'과 '체구({physique})'를 **최우선**으로 고려하여 조언해주세요.
                       예를 들어, 고객이 "종아리가 두껍다"고 했다면, 반바지나 스키니진 추천은 절대 금지입니다.
                    2. 골격({shape_kor})은 세부 조정 용도로 참고하며, 전체 비율 보정에 사용합니다.
                    3. 유행, 개성, 성별 고정관념은 배제하고, **'어떤 환경에서도 민망하지 않은 스타일'**을 제안하세요.
                    4. 고객에게 "왜 이걸 입어야 하는지", "왜 저건 피해야 하는지"를 **납득 가능한 논리로** 설명하세요.
                    5. 애매한 단어는 금지. 오직 구조, 비율, 시각적 착시 효과 같은 **객관적 언어**만 사용하세요.
                    
                    [요청 결과]
                    다른 부연 설명 없이, 반드시 아래 키를 가진 **JSON 형식**으로만 응답하세요.
                    {{
                        "recommendations": "고객의 고민을 해결할 수 있는 현실적인 아이템 5가지를 제시.",
                        "style_tips": "고객의 개인적인 고민과 체형 데이터를 종합하여, 이를 해결할 수 있는 구체적인 스타일링 방법을 3~4문장으로 설명."
                    }}
                    """
                    
                    client = openai.OpenAI(api_key=api_key)
                    response = client.chat.completions.create(model="gpt-4o-mini", response_format={"type": "json_object"}, messages=[{"role": "user", "content": prompt}])
                    ai_response = json.loads(response.choices[0].message.content)
                    
                    ai_recommendations = ai_response.get("recommendations", "")
                    ai_style_tips = ai_response.get("style_tips", "")
                
                except Exception as e:
                    print(f"OpenAI API 호출 오류: {e}")
            
            # ✅ 수정: 사용자의 고민도 분석 데이터로 함께 저장
            analysis_instance.body_shape = body_shape
            analysis_instance.analysis_data = {**geometric_data, "physique": physique, "bmi": bmi, "user_concerns": user_concerns}
            analysis_instance.skeleton_image.name = os.path.join('body_analysis', 'skeleton', skeleton_image_name)
            analysis_instance.recommendations = ai_recommendations
            analysis_instance.style_tips = ai_style_tips
            analysis_instance.save()
            
            return JsonResponse({
                'status': 'success',
                'body_shape': f"{physique}이면서 {shape_kor}",
                'skeleton_image_url': analysis_instance.skeleton_image.url,
                'recommendations': analysis_instance.recommendations,
                'style_tips': analysis_instance.style_tips,
            })
        else:
            analysis_instance.delete()
            return JsonResponse({'status': 'error', 'message': message})
            
    except Exception as e:
        traceback.print_exc()
        if 'analysis_instance' in locals() and analysis_instance.pk:
            analysis_instance.delete()
        return JsonResponse({'status': 'error', 'message': '서버 내부에서 분석 중 오류가 발생했습니다. 관리자에게 문의하세요.'}, status=500)