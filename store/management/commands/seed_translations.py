# store/management/commands/seed_translations.py
from django.core.management.base import BaseCommand
from store.models import BrandCategory, Tag

class Command(BaseCommand):
    help = 'Seeds predefined English and Spanish translations for specific categories and tags.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Starting to seed translations for Categories and Tags ---"))

        # 1. 카테고리 번역 데이터 정의
        # Key: 한국어 이름, Value: {'en': 영어 번역, 'es': 스페인어 번역}
        category_translations = {
            '잡화/액세서리': {'en': 'Accessories', 'es': 'Accesorios'},
            '보충제': {'en': 'Supplements', 'es': 'Suplementos'},
            '운동용품': {'en': 'Equipment', 'es': 'Equipo'},
            '의류': {'en': 'Apparel', 'es': 'Ropa'},
        }

        # 2. 태그 번역 데이터 정의
        tag_translations = {
            '프리미엄': {'en': 'Premium', 'es': 'Prémium'},
            '국산': {'en': 'Domestic', 'es': 'Nacional'},
            '가성비': {'en': 'Cost-effective', 'es': 'Rentable'},
            '초심자용': {'en': 'For Beginners', 'es': 'Para Principiantes'},
            '기능성': {'en': 'Functional', 'es': 'Funcional'},
            '글로벌': {'en': 'Global', 'es': 'Global'},
            '전문가용': {'en': 'For Experts', 'es': 'Para Expertos'},
            'WPI': {'en': 'WPI', 'es': 'WPI'},  # Whey Protein Isolate, 고유명사 그대로
            '다이어트': {'en': 'Diet', 'es': 'Dieta'},
            '비건': {'en': 'Vegan', 'es': 'Vegano'},
        }

        # 3. 카테고리 번역 실행
        self.stdout.write("\nProcessing Brand Categories...")
        for category in BrandCategory.objects.all():
            if category.name_ko in category_translations:
                translations = category_translations[category.name_ko]
                category.name_en = translations['en']
                category.name_es = translations['es']
                # 변경된 _en, _es 필드만 저장
                category.save(update_fields=['name_en', 'name_es'])
                self.stdout.write(self.style.SUCCESS(f"  > Translated '{category.name_ko}' to EN: '{category.name_en}', ES: '{category.name_es}'"))

        # 4. 태그 번역 실행
        self.stdout.write("\nProcessing Tags...")
        for tag in Tag.objects.all():
            if tag.name_ko in tag_translations:
                translations = tag_translations[tag.name_ko]
                tag.name_en = translations['en']
                tag.name_es = translations['es']
                # 변경된 _en, _es 필드만 저장
                tag.save(update_fields=['name_en', 'name_es'])
                self.stdout.write(self.style.SUCCESS(f"  > Translated '{tag.name_ko}' to EN: '{tag.name_en}', ES: '{tag.name_es}'"))
        
        self.stdout.write(self.style.SUCCESS("\n--- Translation seeding complete! ---"))