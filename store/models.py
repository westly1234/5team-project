# store/models.py

from django.db import models

class Brand(models.Model):
    # 카테고리 선택지를 미리 정의합니다.
    CATEGORY_CHOICES = [
        ('APPAREL', '의류'),
        ('EQUIPMENT', '장비'),
        ('SUPPLEMENTS', '보충제'),
        ('ACCESSORIES', '액세서리'),
        ('ETC', '기타'),
    ]

    name = models.CharField(max_length=100, verbose_name="브랜드명", unique=True)
    link = models.URLField(verbose_name="브랜드 링크")
    thumbnail = models.ImageField(upload_to='brand_thumbnails/', verbose_name="썸네일", blank=True, null=True)
    
    # ✅ [추가] 카테고리 필드
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='ETC', # 기본값은 '기타'로 설정
        verbose_name="카테고리"
    )
    # ✅ [추가] 간단 설명 필드
    short_description = models.CharField(
        max_length=150,
        blank=True, # 비워둬도 괜찮음
        verbose_name="간단 설명"
    )
    # ✅ [추가] 추천 브랜드 지정 여부 필드
    is_featured = models.BooleanField(
        default=False,
        verbose_name="추천 브랜드 지정"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "추천 브랜드"
        verbose_name_plural = "추천 브랜드 목록"
        ordering = ['name']

# Product 모델은 그대로 둡니다.
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