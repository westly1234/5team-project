# store/management/commands/sync_db_from_json.py
import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
# 번역이 필요한 모든 모델을 가져옵니다.
from store.models import BrandCategory, Tag

class Command(BaseCommand):
    help = 'Syncs database fields with translations from locales/*.json files.'

    def handle(self, *args, **options):
        self.stdout.write("Starting database synchronization from JSON files...")

        # 처리할 모델과 필드를 딕셔너리로 정의 (모델명 소문자, 실제 모델 클래스, 번역할 필드 리스트)
        models_to_sync = {
            'brandcategory': (BrandCategory, ['name']),
            'tag': (Tag, ['name']),
        }

        # settings.py에 정의된 모든 언어에 대해 반복 (ko, en, es)
        for lang_code, _ in settings.LANGUAGES:
            file_path = os.path.join(settings.BASE_DIR, 'locales', f'{lang_code}.json')

            if not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(f'File not found for language "{lang_code}", skipping.'))
                continue

            with open(file_path, 'r', encoding='utf-8') as f:
                translations = json.load(f)
            
            self.stdout.write(self.style.SUCCESS(f'--- Processing: {lang_code}.json ---'))

            # 정의된 모든 모델에 대해 반복
            for model_name, (Model, fields) in models_to_sync.items():
                # 해당 모델의 모든 객체를 가져와서 반복 (예: 모든 Brand 객체)
                for instance in Model.objects.all():
                    # 번역할 필드들에 대해 반복 (예: name, description)
                    for field_name in fields:
                        # JSON 키 생성 (예: 'brand_15_name')
                        json_key = f'{model_name}_{instance.pk}_{field_name}'

                        # JSON 파일에 해당 키가 있다면
                        if json_key in translations:
                            # modeltranslation 필드 이름 생성 (예: 'name_ko', 'description_en')
                            modeltranslation_field = f'{field_name}_{lang_code}'
                            # setattr을 사용해 객체의 해당 필드에 번역된 값을 할당
                            setattr(instance, modeltranslation_field, translations[json_key])
                            # 변경사항 저장
                            instance.save()
                
                self.stdout.write(f'  > Synced {model_name} model for {lang_code}.')

        self.stdout.write(self.style.SUCCESS("Synchronization complete!"))