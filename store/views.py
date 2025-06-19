# store/views.py

from django.shortcuts import render
from .models import Brand
from django.db.models import Q
from django.core.paginator import Paginator

def store_page_view(request):
    starts_with = request.GET.get('starts_with', None)
    query = request.GET.get('q', None)
    category = request.GET.get('category', None)

    brands_queryset = Brand.objects.filter(is_featured=False).order_by('name')
    featured_brands = Brand.objects.filter(is_featured=True).order_by('name')

    current_filter_params = ''
    if category:
        brands_queryset = brands_queryset.filter(category=category)
        current_filter_params += f'&category={category}'
    
    if starts_with:
        if starts_with == '0-9': brands_queryset = brands_queryset.filter(name__iregex=r'^[0-9]')
        else: brands_queryset = brands_queryset.filter(name__istartswith=starts_with)
        current_filter_params += f'&starts_with={starts_with}'

    if query:
        brands_queryset = brands_queryset.filter(name__icontains=query)
        current_filter_params += f'&q={query}'

    paginator = Paginator(brands_queryset, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'featured_brands': featured_brands, 'page_obj': page_obj,
        'alphabet': list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'categories': Brand.CATEGORY_CHOICES,
        'current_category': category, 'current_filter': starts_with,
        'search_query': query, 'current_filter_params': current_filter_params,
        'active_menu': 'store',
    }
    return render(request, 'store/store.html', context)