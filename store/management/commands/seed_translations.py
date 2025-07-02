import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from store.models import BrandCategory, Tag

class Command(BaseCommand):
    help = 'Seeds all translation fields for Categories (by code) and Tags (by name_ko).'

    def _load_json_file(self, file_path):
        """Helper function to load a JSON file."""
        if not os.path.exists(file_path):
            self.stdout.write(self.style.WARNING(f"File not found: {file_path}"))
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f"Could not parse JSON from: {file_path}"))
            return None

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Starting to seed translations ---"))

        # --- 1. 카테고리 코드와 한국어 키를 매핑하는 딕셔너리 ---
        CATEGORY_CODE_TO_KOREAN_KEY_MAP = {
            "APPAREL": "의류",
            "EQUIPMENT": "운동용품",
            "SUPPLEMENTS": "보충제",
            "ACCESSORIES": "잡화/액세서리",
        }

        # 2. 모든 언어의 번역 파일을 로드합니다. (키: 한국어)
        ko_translations = self._load_json_file(os.path.join(settings.BASE_DIR, 'locales', 'ko.json'))
        en_translations = self._load_json_file(os.path.join(settings.BASE_DIR, 'locales', 'en.json'))
        es_translations = self._load_json_file(os.path.join(settings.BASE_DIR, 'locales', 'es.json'))

        if not all([ko_translations, en_translations, es_translations]):
            self.stdout.write(self.style.ERROR("Could not load all translation files. Aborting."))
            return

        # 3. 카테고리(BrandCategory) 번역 실행 (코드를 기준으로)
        self.stdout.write("\nProcessing Brand Categories...")
        categories_to_update = []
        for category in BrandCategory.objects.all():
            code = category.code # 실제 필드 이름이 'code'라고 가정
            korean_key = CATEGORY_CODE_TO_KOREAN_KEY_MAP.get(code)
            
            if not korean_key:
                self.stdout.write(self.style.WARNING(f"  > No mapping found for category code: '{code}'. Skipping."))
                continue

            ko_name = ko_translations.get(korean_key)
            en_name = en_translations.get(korean_key)
            es_name = es_translations.get(korean_key)

            if all([ko_name, en_name, es_name]):
                category.name = ko_name
                category.name_ko = ko_name
                category.name_en = en_name
                category.name_es = es_name
                categories_to_update.append(category)

        if categories_to_update:
            BrandCategory.objects.bulk_update(categories_to_update, ['name', 'name_ko', 'name_en', 'name_es'])
            self.stdout.write(self.style.SUCCESS(f"  > Synced translations for {len(categories_to_update)} categories."))

        # 4. 태그(Tag) 번역 실행 (name_ko를 기준으로)
        self.stdout.write("\nProcessing Tags...")
        tags_to_update = []
        for tag in Tag.objects.all():
            # ✨ [핵심 수정] DB에 있는 name_ko를 직접 JSON 키로 사용합니다.
            korean_key = tag.name_ko
            
            if not korean_key:
                self.stdout.write(self.style.WARNING(f"  > Skipping Tag ID {tag.pk} because 'name_ko' is empty."))
                continue

            en_name = en_translations.get(korean_key)
            es_name = es_translations.get(korean_key)

            # name_ko는 이미 있으므로, 나머지 필드만 채웁니다.
            if en_name and es_name:
                tag.name = korean_key # 원본 필드도 채워줍니다.
                tag.name_en = en_name
                tag.name_es = es_name
                tags_to_update.append(tag)
        
        if tags_to_update:
            # ✨ [핵심 수정] name_ko는 업데이트할 필요 없으므로 목록에서 제외
            Tag.objects.bulk_update(tags_to_update, ['name', 'name_en', 'name_es'])
            self.stdout.write(self.style.SUCCESS(f"  > Synced translations for {len(tags_to_update)} tags."))
        
        self.stdout.write(self.style.SUCCESS("\n--- Translation seeding complete! ---"))