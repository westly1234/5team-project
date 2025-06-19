# store/management/commands/link_logos.py

import os
import re
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from store.models import Brand

class Command(BaseCommand):
    help = 'Links existing logo files in media folder to their corresponding Brand objects with flexible matching.'

    def handle(self, *args, **kwargs):
        thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'brand_thumbnails')
        if not os.path.isdir(thumbnail_dir):
            self.stderr.write(self.style.ERROR(f'Thumbnail directory not found: {thumbnail_dir}'))
            return

        available_files = {f.lower(): f for f in os.listdir(thumbnail_dir)}
        brands_to_link = Brand.objects.filter(thumbnail__isnull=True)

        if not brands_to_link.exists():
            self.stdout.write(self.style.SUCCESS('All brands already have thumbnails linked.'))
            return

        self.stdout.write(f'Found {brands_to_link.count()} brands to link. Starting process...')
        
        linked_count = 0
        not_found_count = 0

        for brand in brands_to_link:
            # 브랜드 이름을 검색하기 좋은 형태로 바꿉니다 (소문자, 특수문자 제거).
            sanitized_brand_name = re.sub(r'[^a-zA-Z0-9]', '', brand.name).lower()
            
            found_file_key = None
            
            # ✅ [업그레이드] 매칭 로직을 더 유연하게 변경합니다.
            # 1. 먼저, 정확히 일치하는 파일이 있는지 찾아봅니다 (예: 'arle.png').
            for ext in ['.png', '.jpg', '.jpeg', '.webp']:
                exact_match_key = f'{sanitized_brand_name}{ext}'
                if exact_match_key in available_files:
                    found_file_key = exact_match_key
                    break
            
            # 2. 정확히 일치하는 파일이 없다면, 이름의 일부가 포함된 파일을 찾아봅니다.
            if not found_file_key:
                for file_key in available_files.keys():
                    file_name_without_ext = os.path.splitext(file_key)[0]
                    if sanitized_brand_name in file_name_without_ext:
                        found_file_key = file_key
                        break

            if found_file_key:
                original_filename = available_files[found_file_key]
                file_path = os.path.join(thumbnail_dir, original_filename)
                try:
                    with open(file_path, 'rb') as f:
                        brand.thumbnail.save(original_filename, File(f), save=True)
                    self.stdout.write(self.style.SUCCESS(f'  [LINKED] "{brand.name}" -> {original_filename}'))
                    linked_count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  [FAILED] Could not link "{brand.name}": {e}'))
            else:
                self.stdout.write(self.style.WARNING(f'  [NOT FOUND] No matching file found for "{brand.name}"'))
                not_found_count += 1

        self.stdout.write(self.style.SUCCESS(f'\n--- Linking complete! ---'))
        self.stdout.write(f'{linked_count} logos were successfully linked.')
        if not_found_count > 0:
            self.stdout.write(self.style.WARNING(f'{not_found_count} logos could not be found.'))