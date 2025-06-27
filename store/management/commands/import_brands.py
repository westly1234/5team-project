# store/management/commands/import_brands.py

import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Brand  # Tag 모델은 지금 당장 필요 없으므로 제거

class Command(BaseCommand):
    help = 'Import or update brand data from a CSV file (name, link, thumbnail path).'

    def handle(self, *args, **kwargs):
        file_name = 'brands_exported.csv' 
        file_path = os.path.join(settings.BASE_DIR, file_name)

        # ✅ [핵심 변경] 헤더가 없는 CSV 파일을 읽기 위해 기본 csv.reader를 사용합니다.
        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                
                created_count = 0
                updated_count = 0
                skipped_count = 0

                for i, row in enumerate(reader):
                    # 행에 최소 3개의 열이 있는지 확인 (name, link, thumbnail)
                    if len(row) < 3:
                        self.stdout.write(self.style.WARNING(f'Skipping row {i+1}: not enough columns.'))
                        skipped_count += 1
                        continue
                        
                    brand_name = row[0].strip()
                    brand_link = row[1].strip()
                    # 썸네일 경로는 DB의 'brand_thumbnails/' 부분을 제외하고 파일명만 저장해야 합니다.
                    # 예: /media/brand_thumbnails/4monster.png -> 4monster.png
                    thumbnail_path = row[2].strip()
                    
                    # ✅ [핵심 변경] Brand 모델의 ImageField에 저장될 형식으로 경로를 가공합니다.
                    # ImageField는 MEDIA_ROOT를 기준으로 하위 경로만 저장합니다.
                    # 예: 'brand_thumbnails/4monster.png'
                    if thumbnail_path.startswith('/media/'):
                        # '/media/' 부분을 제거합니다.
                        thumbnail_db_path = thumbnail_path.replace('/media/', '', 1)
                    else:
                        thumbnail_db_path = thumbnail_path

                    if not brand_name or not brand_link:
                        self.stdout.write(self.style.WARNING(f'Skipping row {i+1}: name or link is empty.'))
                        skipped_count += 1
                        continue

                    # ✅ [핵심 변경] Brand 모델 필드에 맞게 defaults 딕셔너리를 구성합니다.
                    # 지금은 link와 thumbnail만 업데이트/생성합니다.
                    brand_defaults = {
                        'link': brand_link,
                        'thumbnail': thumbnail_db_path, # 가공된 경로를 저장
                    }

                    # 'name'을 기준으로 객체를 찾거나, 없으면 새로 만듭니다.
                    brand, created = Brand.objects.update_or_create(
                        name=brand_name,
                        defaults=brand_defaults
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'CREATED: "{brand.name}"'))
                    else:
                        updated_count += 1
                        self.stdout.write(self.style.WARNING(f'UPDATED: "{brand.name}"'))
            
            self.stdout.write(self.style.SUCCESS(f'\n--- Import complete! ---'))
            self.stdout.write(f'  - {created_count} brands created.')
            self.stdout.write(f'  - {updated_count} brands updated.')
            self.stdout.write(f'  - {skipped_count} rows skipped.')

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found at: {file_path}.'))
            self.stderr.write(self.style.WARNING(f"Please make sure '{file_name}' is in the project root directory."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An unexpected error occurred: {e}'))