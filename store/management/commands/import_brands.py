# store/management/commands/import_brands.py

import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Brand

# ✅ [핵심] Django가 찾는 것은 바로 이 'Command' 클래스입니다.
class Command(BaseCommand):
    help = 'Import brands from a CSV file into the Brand model. It updates existing entries if the link has changed.'

    def handle(self, *args, **kwargs):
        # 가져올 CSV 파일의 이름을 지정합니다.
        file_name = 'brands_exported.csv' 
        file_path = os.path.join(settings.BASE_DIR, file_name)

        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.reader(csvfile)
                
                # CSV 파일의 첫 줄(헤더)은 건너뜁니다.
                next(reader, None)  
                
                created_count = 0
                updated_count = 0

                for row in reader:
                    if len(row) < 2:
                        continue
                        
                    brand_name = row[0].strip()
                    brand_link = row[1].strip()

                    if not brand_name or not brand_link:
                        continue

                    # 'name'을 기준으로 객체를 찾거나, 없으면 새로 만듭니다.
                    obj, created = Brand.objects.get_or_create(
                        name=brand_name,
                        defaults={'link': brand_link}
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Successfully created brand: "{brand_name}"'))
                    else:
                        # 이미 존재하면 링크가 다른 경우에만 업데이트합니다.
                        if obj.link != brand_link:
                            obj.link = brand_link
                            obj.save()
                            updated_count += 1
                            self.stdout.write(self.style.WARNING(f'Updated link for existing brand: "{brand_name}"'))
            
            self.stdout.write(self.style.SUCCESS(f'\n--- Import complete! ---'))
            self.stdout.write(f'{created_count} brands created.')
            self.stdout.write(f'{updated_count} brands updated.')

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found at: {file_path}.'))
            self.stderr.write(self.style.WARNING(f"Please make sure '{file_name}' is in the project root directory."))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred: {e}'))