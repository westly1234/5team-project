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

# 기존 모델들 아래에 추가
class BodyShapeAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    source_image = models.ImageField(upload_to='body_analysis/source/')
    
    # ✅ 추가: 스켈레톤 이미지를 저장할 필드
    skeleton_image = models.ImageField(upload_to='body_analysis/skeleton/', blank=True, null=True)
    analysis_image = models.ImageField(upload_to='body_analysis/analysis_results/', blank=True, null=True)

    body_shape_choices = [
        ('HOURGLASS', '모래시계형'),
        ('TRIANGLE', '삼각형 (서양배형)'),
        ('INVERTED_TRIANGLE', '역삼각형'),
        ('RECTANGLE', '직사각형'),
        ('OVAL', '타원형 (사과형)'),
    ]
    body_shape = models.CharField(max_length=20, choices=body_shape_choices, blank=True, null=True)
    analysis_data = models.JSONField(blank=True, null=True) # 신체 비율 등 수치 데이터 저장

    # ✅ 추가: AI가 생성한 추천 내용을 저장할 필드
    recommendations = models.TextField(blank=True, null=True)
    style_tips = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

class ClothingRecommendation(models.Model):
    body_shape = models.CharField(max_length=20, choices=BodyShapeAnalysis.body_shape_choices, unique=True)
    recommended_fits = models.TextField(help_text="추천하는 옷 스타일 (예: A라인 스커트, 와이드 팬츠, 보트넥 티셔츠)을 쉼표로 구분하여 입력")
    style_tips = models.TextField(help_text="스타일링 팁 요약")

    def __str__(self):
        return self.get_body_shape_display()