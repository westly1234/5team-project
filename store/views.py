# store/views.py

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
from .body_shape_logic import analyze_body_shape_advanced
import json
import os
import openai
import traceback
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import numpy as np
import uuid

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    print("pillow-heif 라이브러리가 설치되지 않았습니다. HEIC/HEIF 파일은 지원되지 않습니다.")

# ==========================================================
#  페이지 렌더링 뷰 및 기타 API (이전과 동일)
# ==========================================================
# ... (다른 모든 뷰 함수는 이전과 동일하므로 생략합니다) ...
def store_home_view(request):
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
        'page_obj': page_obj, 'alphabet': list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        'categories': BrandCategory.objects.all().order_by('name'), 'current_category': category_code,
        'current_filter': starts_with, 'search_query': query, 'current_filter_params': current_filter_params,
        'active_menu': 'store', 'favorite_brand_ids': favorite_brand_ids,
    }
    return render(request, 'store/store.html', context)

@login_required
def favorite_brands_view(request):
    favorite_brands = request.user.favorite_brands.all().prefetch_related('categories')
    favorite_brand_ids = favorite_brands.values_list('id', flat=True)
    context = {'favorite_brands': favorite_brands, 'favorite_brand_ids': favorite_brand_ids, 'active_menu': 'store'}
    return render(request, 'store/my_favorites.html', context)

def brand_finder_view(request):
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
            'is_result': True, 'active_menu': 'store',
        }
        return render(request, 'store/brand_finder.html', context)
    context = {'categories': BrandCategory.objects.all().order_by('name'), 'is_result': False, 'active_menu': 'store'}
    return render(request, 'store/brand_finder.html', context)

def compare_page_view(request):
    context = {'ids': request.GET.get('ids', ''), 'active_menu': 'store'}
    return render(request, 'store/compare_page.html', context)

@login_required
def body_shape_analyzer_view(request):
    try:
        import cv2, mediapipe
        library_installed = True
    except ImportError:
        library_installed = False
    return render(request, 'store/body_shape_analyzer.html', {'library_installed': library_installed})

def brand_detail_api(request, brand_id):
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
    """
    AJAX 요청을 받아 필터링된 브랜드 목록 HTML을 JSON으로 반환합니다.
    (찜하기, 비교하기 기능에 필요한 모든 데이터를 포함합니다)
    """
    # 1. 모든 브랜드를 기본 쿼리셋으로 설정합니다.
    brands_queryset = Brand.objects.all().prefetch_related('categories', 'tags')
    
    # 2. 현재 로그인한 사용자가 찜한 브랜드 ID 목록을 가져옵니다.
    # 이 데이터는 _brand_card.html에서 '찜하기' 버튼의 초기 상태를 결정하는 데 사용됩니다.
    favorite_brand_ids = request.user.favorite_brands.values_list('id', flat=True) if request.user.is_authenticated else []
    
    # 3. GET 파라미터에서 필터링 조건들을 가져옵니다.
    category_code = request.GET.get('category')
    starts_with = request.GET.get('starts_with')
    query = request.GET.get('q')

    # 4. 페이지네이션을 위한 현재 필터 파라미터 문자열을 생성합니다.
    current_filter_params_dict = request.GET.copy()
    if 'page' in current_filter_params_dict:
        del current_filter_params_dict['page']
    current_filter_params = '&' + current_filter_params_dict.urlencode() if current_filter_params_dict else ''

    # 5. 조건에 따라 쿼리셋을 필터링합니다.
    if category_code:
        brands_queryset = brands_queryset.filter(categories__code=category_code)
    if starts_with:
        if starts_with == '0-9':
            brands_queryset = brands_queryset.filter(name__iregex=r'^[0-9]')
        else:
            brands_queryset = brands_queryset.filter(name__istartswith=starts_with)
    if query:
        brands_queryset = brands_queryset.filter(name__icontains=query)

    # 6. 필터링된 결과를 페이지네이션합니다.
    paginator = Paginator(brands_queryset.distinct().order_by('name'), 24) # 한 페이지에 24개씩 표시
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 7. 템플릿에 전달할 context 데이터를 구성합니다.
    # _brand_card.html에서 favorite_brand_ids를 사용하므로 반드시 포함해야 합니다.
    context = {
        'page_obj': page_obj,
        'favorite_brand_ids': favorite_brand_ids,
        'search_query': query,
        'current_filter_params': current_filter_params
    }
    
    # 8. context 데이터를 사용하여 brand_grid.html 템플릿을 HTML 문자열로 렌더링합니다.
    # 이 때, brand_grid.html 안에서 'store/partials/_brand_card.html'을 올바른 경로로 include해야 합니다.
    brands_html = render_to_string('store/partials/brand_grid.html', context, request=request)
    
    # 9. 렌더링된 HTML을 JSON 형식으로 응답합니다.
    return JsonResponse({'brands_html': brands_html})
# ==========================================================
#  체형 분석 기능 (실루엣 형태 분석 업그레이드)
# ==========================================================
@login_required
def analyze_body_shape_api(request):
    """프로필 정보와 이미지의 실루엣 형태를 결합하여 초개인화된 AI 스타일링 팁을 생성합니다."""
    if request.method != 'POST' or not request.FILES.get('image'):
        return JsonResponse({'status': 'error', 'message': '잘못된 요청입니다.'}, status=400)
    
    # 1. 고객 데이터 로딩
    try:
        profile = request.user.profile
        if not profile.height or not profile.current_weight:
            return JsonResponse({'status': 'error', 'message': '체형 분석을 위해 프로필에 키와 현재 체중을 먼저 입력해주세요.'}, status=400)
        height_m = profile.height / 100
        bmi = profile.current_weight / (height_m ** 2)
        physique = "표준 체형"
        if bmi < 18.5: physique = "마른 체형"
        elif 25 <= bmi < 30: physique = "과체중"
        elif bmi >= 30: physique = "비만 체형"
    except Exception:
        return JsonResponse({'status': 'error', 'message': '프로필 정보를 찾을 수 없습니다.'}, status=404)
    
    gender = request.POST.get('gender')
    if gender not in ['male', 'female']:
        return JsonResponse({'status': 'error', 'message': '성별을 선택해주세요.'}, status=400)
    user_concerns = request.POST.get('concerns', '').strip()

    # 2. 이미지 처리 (안전한 파일 이름 생성 포함)
    image_file = request.FILES['image']
    if image_file.size > 10 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'message': '이미지 파일은 10MB를 초과할 수 없습니다.'})
    try:
        img = Image.open(image_file)
        if hasattr(img, '_getexif'):
            exif = img._getexif()
            if exif:
                orientation_key = 274
                if orientation_key in exif:
                    orientation = exif[orientation_key]
                    if orientation == 3: img = img.rotate(180, expand=True)
                    elif orientation == 6: img = img.rotate(270, expand=True)
                    elif orientation == 8: img = img.rotate(90, expand=True)
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024))
        output = BytesIO()
        img.convert('RGB').save(output, format='JPEG', quality=85)
        output.seek(0)
        safe_filename = f"{uuid.uuid4()}.jpg"
        image_file_to_save = ContentFile(output.read(), name=safe_filename)
    except UnidentifiedImageError:
        return JsonResponse({'status': 'error', 'message': '지원하지 않는 이미지 형식입니다. JPG, PNG, HEIC 파일을 이용해주세요.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'이미지 처리 중 오류가 발생했습니다: {e}'}, status=400)

    # 3. 분석 인스턴스 생성 및 이미지 저장
    analysis_instance = BodyShapeAnalysis(user=request.user)
    analysis_instance.source_image.save(image_file_to_save.name, image_file_to_save, save=True)
    
    # 4. 분석 결과 이미지들을 저장할 경로 설정
    base_filename = os.path.basename(analysis_instance.source_image.name)
    skeleton_image_name = f"skeleton_{base_filename}"
    analysis_image_name = f"analysis_{base_filename}"
    
    skeleton_folder = os.path.join(settings.MEDIA_ROOT, 'body_analysis', 'skeleton')
    os.makedirs(skeleton_folder, exist_ok=True)
    skeleton_image_path = os.path.join(skeleton_folder, skeleton_image_name)

    analysis_folder = os.path.join(settings.MEDIA_ROOT, 'body_analysis', 'analysis_results')
    os.makedirs(analysis_folder, exist_ok=True)
    analysis_image_path = os.path.join(analysis_folder, analysis_image_name)

    try:
        # 5. 새로운 고급 분석 함수 호출
        body_shape, new_analysis_data, message = analyze_body_shape_advanced(
            analysis_instance.source_image.path, 
            skeleton_image_path,
            analysis_image_path
        )
        
        if body_shape:
            # 6. OpenAI API 호출
            api_key = os.getenv("OPENAI_API_KEY")
            ai_recommendations, ai_style_tips = "추천 생성 오류", "스타일팁 생성 오류"
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
                    - 실루엣 형태: {shape_kor}
                    - 사용자 개인 고민: "{user_concerns if user_concerns else "특별한 고민 없음"}"

                    [지시사항]
                    1. '사용자 개인 고민'과 '체구({physique})'를 **최우선**으로 고려하여 조언해주세요.
                       예를 들어, 고객이 "종아리가 두껍다"고 했다면, 반바지나 스키니진 추천은 절대 금지입니다.
                    2. 실루엣 형태({shape_kor})는 세부 조정 용도로 참고하며, 전체 비율 보정에 사용합니다.
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
                    ai_recommendations = ai_response.get("recommendations", ai_recommendations)
                    ai_style_tips = ai_response.get("style_tips", ai_style_tips)
                except Exception as e:
                    print(f"OpenAI API 호출 오류: {e}")
            
            # 7. 최종 결과 DB에 저장
            analysis_instance.body_shape = body_shape
            
            # ✅ NumPy 타입을 파이썬 기본 타입으로 변환 (bool_ 처리 추가)
            shape_data = new_analysis_data.get('shape_analysis', {})
            for key, value in shape_data.items():
                if isinstance(value, (np.integer, np.int64)):
                    shape_data[key] = int(value)
                elif isinstance(value, (np.floating, np.float64)):
                    shape_data[key] = float(value)
                elif isinstance(value, np.bool_): # NumPy 불리언 타입 처리
                    shape_data[key] = bool(value)

            analysis_instance.analysis_data = {
                'shape_analysis': shape_data, 
                "profile_based": {
                    "physique": physique, "bmi": round(bmi, 2), "user_concerns": user_concerns
                }
            }
            analysis_instance.skeleton_image.name = f"body_analysis/skeleton/{skeleton_image_name}"
            analysis_instance.analysis_image.name = f"body_analysis/analysis_results/{analysis_image_name}"
            analysis_instance.recommendations = ai_recommendations
            analysis_instance.style_tips = ai_style_tips
            analysis_instance.save()
            
            # 8. API 응답 반환
            return JsonResponse({
                'status': 'success',
                'body_shape': f"{physique}이면서 {dict(BodyShapeAnalysis.body_shape_choices).get(body_shape, '분석 불가')}",
                'skeleton_image_url': analysis_instance.skeleton_image.url,
                'analysis_image_url': analysis_instance.analysis_image.url,
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