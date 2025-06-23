# store/models.py

from django.db import models
from django.conf import settings
from django.db.models import Avg

class BrandCategory(models.Model):
    """브랜드 카테고리(의류, 운동용품 등)를 위한 모델"""
    code = models.CharField(max_length=20, unique=True, verbose_name="카테고리 코드")
    name = models.CharField(max_length=50, verbose_name="카테고리명")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "브랜드 카테고리"
        verbose_name_plural = "브랜드 카테고리 목록"

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="태그명")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "핵심 태그"
        verbose_name_plural = "핵심 태그 목록"

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="브랜드명")
    link = models.URLField(verbose_name="브랜드 링크")
    thumbnail = models.ImageField(upload_to='brand_thumbnails/', blank=True, null=True, verbose_name="썸네일 이미지")
    
    categories = models.ManyToManyField(
        BrandCategory, 
        related_name='brands', 
        blank=True,
        verbose_name="카테고리"
    )

    description = models.CharField(max_length=200, blank=True, verbose_name="짧은 설명 (카드 표시용)")
    detailed_description = models.TextField(blank=True, verbose_name="상세 설명 (모달 표시용)")
    is_featured = models.BooleanField(default=False, verbose_name="추천 브랜드 여부")
    promotion_info = models.CharField(max_length=50, blank=True, verbose_name="프로모션 정보")
    tags = models.ManyToManyField('Tag', blank=True, related_name='brands', verbose_name="핵심 태그")
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorite_brands', blank=True, verbose_name="찜한 사용자")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return self.name
    def get_average_rating(self): return self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    class Meta:
        ordering = ['name']
        verbose_name = "브랜드"
        verbose_name_plural = "브랜드 목록"

class Review(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='reviews', verbose_name="브랜드")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews', verbose_name="작성자")
    rating = models.PositiveSmallIntegerField(choices=[(i, f'{i}점') for i in range(1, 6)], verbose_name="평점")
    content = models.TextField(verbose_name="리뷰 내용")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('brand', 'user')
        verbose_name = "브랜드 리뷰"
        verbose_name_plural = "브랜드 리뷰 목록"

    def __str__(self):
        return f'{self.user.username}의 {self.brand.name} 리뷰'

class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="상품명")
    description = models.TextField(verbose_name="설명", blank=True)
    thumbnail = models.ImageField(upload_to='store_thumbnails/', verbose_name="썸네일")
    product_link = models.URLField(verbose_name="상품 링크")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "추천 상품"
        verbose_name_plural = "추천 상품 목록"
        ordering = ['-created_at']