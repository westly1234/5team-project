# store/views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from .models import Brand, Tag, Review, BrandCategory, Product
import json
import os
import openai

def store_home_view(request):
    """스토어 메인 페이지를 렌더링합니다."""
    # ✅ 수정: filter_brands_api와 동일한 로직을 사용하도록 변경
    # 이렇게 하면 초기 페이지 로드 시 필요한 모든 컨텍스트를 가지게 됩니다.
    brands_queryset = Brand.objects.all().prefetch_related('categories', 'tags')

    favorite_brand_ids = []
    if request.user.is_authenticated:
        favorite_brand_ids = request.user.favorite_brands.values_list('id', flat=True)

    category_code = request.GET.get('category')
    starts_with = request.GET.get('starts_with')
    query = request.GET.get('q')
    current_filter_params = ''

    if category_code:
        brands_queryset = brands_queryset.filter(categories__code=category_code)
        current_filter_params += f'&category={category_code}'
    if starts_with:
        if starts_with == '0-9':
            brands_queryset = brands_queryset.filter(name__iregex=r'^[0-9]')
        else:
            brands_queryset = brands_queryset.filter(name__istartswith=starts_with)
        current_filter_params += f'&starts_with={starts_with}'
    if query:
        brands_queryset = brands_queryset.filter(name__icontains=query)
        current_filter_params += f'&q={query}'

    paginator = Paginator(brands_queryset.distinct().order_by('name'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'alphabet': list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        'categories': BrandCategory.objects.all().order_by('name'),
        'current_category': category_code,
        'current_filter': starts_with, # 'current_filter' 변수 추가
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
    
    context = {
        'favorite_brands': favorite_brands,
        'favorite_brand_ids': favorite_brand_ids,
        'active_menu': 'store',
    }
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

    context = {
        'categories': BrandCategory.objects.all().order_by('name'), 
        'is_result': False,
        'active_menu': 'store',
    }
    return render(request, 'store/brand_finder.html', context)

def compare_page_view(request):
    """브랜드 비교 결과 페이지를 렌더링합니다."""
    context = {
        'ids': request.GET.get('ids', ''),
        'active_menu': 'store',
    }
    return render(request, 'store/compare_page.html', context)

# --- API (Application Programming Interface) 뷰들 ---

def brand_detail_api(request, brand_id):
    """브랜드 상세 정보를 JSON으로 반환하고, 설명이 없으면 AI로 생성합니다."""
    try:
        brand = Brand.objects.get(pk=brand_id)

        # ---- AI 설명 생성 로직 시작 ----
        if not brand.detailed_description:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    categories_str = ", ".join([cat.name for cat in brand.categories.all()])
                    tags_str = ", ".join([tag.name for tag in brand.tags.all()])
                    
                    prompt_text = f"""
                    헬스/피트니스 브랜드 '{brand.name}'에 대한 간결하고 매력적인 한국어 소개글을 3~4문장으로 작성해줘.
                    이 브랜드의 주요 정보는 다음과 같아:
                    - 카테고리: {categories_str if categories_str else '정보 없음'}
                    - 핵심 태그: {tags_str if tags_str else '정보 없음'}
                    결과는 다른 부연 설명 없이, 생성된 소개글 텍스트만 깔끔하게 출력해줘.
                    """
                    
                    client = openai.OpenAI(api_key=api_key)
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful marketing copywriter specializing in fitness brands."},
                            {"role": "user", "content": prompt_text}
                        ],
                        temperature=0.7,
                        max_tokens=300
                    )
                    
                    generated_description = response.choices[0].message.content.strip()
                    brand.detailed_description = generated_description
                    brand.save(update_fields=['detailed_description'])

                except Exception as e:
                    print(f"OpenAI API 호출 중 오류 발생: {e}")
            else:
                print("OPENAI_API_KEY가 설정되지 않았습니다.")
        # ---- AI 설명 생성 로직 끝 ----

        reviews_agg = brand.reviews.aggregate(avg_rating=Avg('rating'), review_count=Count('id'))
        reviews = brand.reviews.select_related('user').order_by('-created_at')[:10]
        reviews_data = [{'user_username': r.user.username, 'rating': r.rating, 'content': r.content, 'created_at': r.created_at.strftime('%Y-%m-%d')} for r in reviews]

        user_review_data = None
        if request.user.is_authenticated:
            user_review = Review.objects.filter(brand=brand, user=request.user).first()
            if user_review:
                user_review_data = {'rating': user_review.rating, 'content': user_review.content}

        data = {
            'id': brand.id, 'name': brand.name, 'link': brand.link,
            'thumbnail_url': brand.thumbnail.url if brand.thumbnail else None,
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

        review, created = Review.objects.update_or_create(
            brand=brand, user=request.user, defaults={'rating': rating, 'content': content}
        )
        message = '리뷰가 성공적으로 등록되었습니다.' if created else '리뷰가 성공적으로 수정되었습니다.'
        return JsonResponse({'status': 'ok', 'message': message})
    return HttpResponseBadRequest("Invalid request method.")

def compare_brands_api(request):
    """브랜드 비교를 위한 데이터를 JSON으로 반환하고, 태그가 없으면 AI로 생성합니다."""
    ids_str = request.GET.get('ids')
    if not ids_str:
        return JsonResponse({'error': 'No brand IDs provided'}, status=400)
    
    ids = [int(id) for id in ids_str.split(',') if id.isdigit()]
    
    brands = Brand.objects.filter(pk__in=ids).annotate(
        avg_rating=Avg('reviews__rating')
    ).prefetch_related('tags', 'categories')
    
    brands_data = []
    for brand in brands:
        if not brand.tags.exists() and brand.detailed_description:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    prompt_text = f"""
                    다음 텍스트에서 이 브랜드를 가장 잘 나타내는 핵심 키워드를 3~4개만 쉼표(,)로 구분해서 한국어로 추출해줘.
                    다른 부연 설명은 전혀 붙이지 말고, 오직 키워드만 '키워드1,키워드2,키워드3' 형식으로 응답해줘.
                    ---
                    텍스트: "{brand.detailed_description}"
                    ---
                    """
                    client = openai.OpenAI(api_key=api_key)
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a helpful keyword extractor that returns only comma-separated keywords in Korean."},
                            {"role": "user", "content": prompt_text}
                        ],
                        temperature=0.3,
                        max_tokens=50
                    )
                    extracted_keywords_str = response.choices[0].message.content.strip()
                    keywords = [kw.strip() for kw in extracted_keywords_str.split(',') if kw.strip()]
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
    
    favorite_brand_ids = []
    if request.user.is_authenticated:
        favorite_brand_ids = request.user.favorite_brands.values_list('id', flat=True)

    category_code = request.GET.get('category')
    starts_with = request.GET.get('starts_with')
    query = request.GET.get('q')
    
    current_filter_params = ''
    if category_code:
        brands_queryset = brands_queryset.filter(categories__code=category_code)
        current_filter_params += f'&category={category_code}'
    if starts_with:
        if starts_with == '0-9':
            brands_queryset = brands_queryset.filter(name__iregex=r'^[0-9]')
        else:
            brands_queryset = brands_queryset.filter(name__istartswith=starts_with)
        current_filter_params += f'&starts_with={starts_with}'
    if query:
        brands_queryset = brands_queryset.filter(name__icontains=query)
        current_filter_params += f'&q={query}'

    paginator = Paginator(brands_queryset.distinct().order_by('name'), 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'favorite_brand_ids': favorite_brand_ids,
        'search_query': query,
        'current_filter_params': current_filter_params,
    }

    brands_html = render_to_string('store/partials/brand_grid.html', context, request=request)
    
    return JsonResponse({'brands_html': brands_html})