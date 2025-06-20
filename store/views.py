# store/views.py

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.contrib.auth.decorators import login_required
from .models import Brand, Tag, Review
import json

def store_home_view(request):
    """
    스토어 메인 페이지를 렌더링합니다.
    모든 브랜드를 가져와서 필터링, 검색, 페이지네이션을 적용합니다.
    """
    # 1. 모든 브랜드를 가져옵니다. (is_featured 구분 없이)
    brands_queryset = Brand.objects.all()

    # 2. 필터링 및 검색 로직
    category = request.GET.get('category')
    starts_with = request.GET.get('starts_with')
    query = request.GET.get('q')
    current_filter_params = ''  # 페이지네이션 링크에 사용할 파라미터

    if category:
        brands_queryset = brands_queryset.filter(category=category)
        current_filter_params += f'&category={category}'
    
    if starts_with:
        if starts_with == '0-9':
            # 이름이 숫자로 시작하는 경우 (정규식 사용)
            brands_queryset = brands_queryset.filter(name__iregex=r'^[0-9]')
        else:
            # 이름이 해당 알파벳으로 시작하는 경우 (대소문자 무시)
            brands_queryset = brands_queryset.filter(name__istartswith=starts_with)
        current_filter_params += f'&starts_with={starts_with}'

    if query:
        # 이름에 검색어가 포함되는 경우 (대소문자 무시)
        brands_queryset = brands_queryset.filter(name__icontains=query)
        current_filter_params += f'&q={query}'

    # 3. 정렬 및 페이지네이션
    paginator = Paginator(brands_queryset.order_by('name'), 24)  # 한 페이지에 24개씩 표시
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 4. 템플릿에 전달할 context 데이터
    context = {
        'page_obj': page_obj,  # 'featured_brands'를 제거하고 'page_obj'에 모든 것을 담습니다.
        'alphabet': list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        'categories': Brand.CATEGORY_CHOICES,
        'current_category': category,
        'current_filter': starts_with,
        'search_query': query,
        'current_filter_params': current_filter_params,
        'active_menu': 'store',
    }
    return render(request, 'store/store.html', context)


def brand_detail_api(request, brand_id):
    """브랜드 상세 정보를 JSON으로 반환하는 API"""
    try:
        brand = Brand.objects.get(pk=brand_id)
        
        # 리뷰 정보도 함께 가져오도록 확장 (평균, 개수)
        reviews_agg = brand.reviews.aggregate(avg_rating=Avg('rating'), review_count=Count('id'))
        reviews = brand.reviews.select_related('user').order_by('-created_at')[:10]
        reviews_data = [{
            'user_username': review.user.username,
            'rating': review.rating,
            'content': review.content,
            'created_at': review.created_at.strftime('%Y-%m-%d')
        } for review in reviews]

        data = {
            'id': brand.id,
            'name': brand.name,
            'link': brand.link,
            # 상세 설명이 없으면, 기본 설명을 대신 보여주고, 그마저도 없으면 기본 텍스트 출력
            'detailed_description': brand.detailed_description or brand.description or "상세 설명이 아직 없습니다.",
            'avg_rating': reviews_agg['avg_rating'] or 0,
            'review_count': reviews_agg['review_count'] or 0,
            'reviews': reviews_data
        }
        return JsonResponse(data)
    except Brand.DoesNotExist:
        return JsonResponse({'error': 'Brand not found'}, status=404)

@login_required
def toggle_favorite_api(request, brand_id):
    """찜하기/취소 기능을 처리하는 API"""
    if request.method == 'POST':
        brand = get_object_or_404(Brand, pk=brand_id)
        user = request.user
        
        if brand in user.favorite_brands.all():
            user.favorite_brands.remove(brand)
            favorited = False
        else:
            user.favorite_brands.add(brand)
            favorited = True
            
        return JsonResponse({'status': 'ok', 'favorited': favorited, 'count': brand.favorited_by.count()})
    return HttpResponseBadRequest("Invalid request method.")

@login_required
def add_review_api(request, brand_id):
    """리뷰 추가/수정을 처리하는 API"""
    if request.method == 'POST':
        brand = get_object_or_404(Brand, pk=brand_id)
        data = json.loads(request.body)
        rating = data.get('rating')
        content = data.get('content')

        if not rating or not content:
            return JsonResponse({'status': 'error', 'message': '평점과 내용을 모두 입력해주세요.'}, status=400)

        review, created = Review.objects.update_or_create(
            brand=brand,
            user=request.user,
            defaults={'rating': rating, 'content': content}
        )
        
        message = '리뷰가 성공적으로 등록되었습니다.' if created else '리뷰가 성공적으로 수정되었습니다.'
        return JsonResponse({'status': 'ok', 'message': message})
    return HttpResponseBadRequest("Invalid request method.")

def compare_brands_api(request):
    """브랜드 비교를 위한 데이터를 JSON으로 반환하는 API"""
    ids_str = request.GET.get('ids')
    if not ids_str:
        return JsonResponse({'error': 'No brand IDs provided'}, status=400)
    
    ids = [int(id) for id in ids_str.split(',') if id.isdigit()]
    
    brands = Brand.objects.filter(pk__in=ids).annotate(
        avg_rating=Avg('reviews__rating')
    ).prefetch_related('tags')
    
    brands_data = []
    for brand in brands:
        brands_data.append({
            'id': brand.id,
            'name': brand.name,
            'thumbnail_url': brand.thumbnail.url if brand.thumbnail else None,
            'category': brand.get_category_display(),
            'link': brand.link,
            'avg_rating': brand.avg_rating or 0,
            'promotion_info': brand.promotion_info,
            'tags': [tag.name for tag in brand.tags.all()]
        })

    return JsonResponse({'brands': brands_data})

def brand_finder_view(request):
    """브랜드 찾기 퀴즈 페이지 렌더링 및 결과 처리"""
    if request.method == 'POST':
        goal = request.POST.get('goal')
        priority = request.POST.get('priority')
        category = request.POST.get('category')

        results = Brand.objects.all()

        if goal == 'diet': results = results.filter(tags__name__in=['다이어트', '저칼로리', '체지방감소'])
        elif goal == 'muscle': results = results.filter(tags__name__in=['단백질', '근성장', 'WPI', '부스터'])
        
        if priority == 'vegan': results = results.filter(tags__name__in=['비건', '자연주의'])
        elif priority == 'cost': results = results.filter(tags__name__in=['가성비'])
        
        if category and category != 'ALL': results = results.filter(category=category)
        
        context = {
            'results': results.distinct().annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')[:5],
            'is_result': True,
        }
        return render(request, 'store/brand_finder.html', context)

    context = {'categories': Brand.CATEGORY_CHOICES, 'is_result': False}
    return render(request, 'store/brand_finder.html', context)

def compare_page_view(request):
    """브랜드 비교 결과 페이지를 렌더링"""
    context = {'ids': request.GET.get('ids', '')}
    return render(request, 'store/compare_page.html', context)