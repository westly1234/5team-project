# store/management/commands/import_brands.py

import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Brand

class Command(BaseCommand):
    help = 'CSV 파일로부터 브랜드 목록을 가져와 Brand 모델에 저장합니다.'

    def handle(self, *args, **kwargs):
        # CSV 파일의 전체 경로를 지정합니다. (프로젝트 루트에 파일이 있다고 가정)
        file_path = os.path.join(settings.BASE_DIR, 'brands_exported.csv')

        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                # CSV 파일에 헤더(첫 줄)가 있다면 건너뜁니다.
                next(reader, None)  
                
                created_count = 0
                updated_count = 0

                for row in reader:
                    # row[0]은 첫 번째 열 (브랜드명), row[1]은 두 번째 열 (링크)
                    brand_name = row[0].strip()
                    brand_link = row[1].strip()

                    # 빈 줄은 건너뜁니다.
                    if not brand_name or not brand_link:
                        continue

                    # Brand 모델에서 해당 이름의 객체가 있으면 가져오고, 없으면 새로 만듭니다.
                    # 이것은 중복 저장을 막아주는 매우 중요한 기능입니다.
                    obj, created = Brand.objects.get_or_create(
                        name=brand_name,
                        defaults={'link': brand_link}
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'새로운 브랜드 생성: "{brand_name}"'))
                    else:
                        # 만약 이미 존재하는 브랜드인데 링크가 다르다면 업데이트합니다.
                        if obj.link != brand_link:
                            obj.link = brand_link
                            obj.save()
                            updated_count += 1
                            self.stdout.write(self.style.WARNING(f'기존 브랜드 링크 업데이트: "{brand_name}"'))
            
            self.stdout.write(self.style.SUCCESS(f'\n--- 임포트 완료! ---'))
            self.stdout.write(f'{created_count}개의 브랜드가 새로 생성되었습니다.')
            self.stdout.write(f'{updated_count}개의 브랜드가 업데이트되었습니다.')

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'파일을 찾을 수 없습니다: {file_path}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'오류 발생: {e}'))