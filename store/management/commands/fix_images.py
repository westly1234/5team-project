# store/management/commands/fix_images.py

import os
from io import BytesIO
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from store.models import Brand
from PIL import Image
import cairosvg

class Command(BaseCommand):
    help = 'Fixes incorrectly saved thumbnails by detecting their true file type and converting them to PNG.'

    def handle(self, *args, **kwargs):
        # 썸네일이 있는 모든 브랜드를 대상으로 작업합니다.
        brands_with_thumbnails = Brand.objects.exclude(thumbnail__isnull=True).exclude(thumbnail__exact='')

        if not brands_with_thumbnails.exists():
            self.stdout.write(self.style.SUCCESS('No thumbnails to process.'))
            return

        self.stdout.write(f'Found {brands_with_thumbnails.count()} brands with thumbnails. Starting verification and fixing process...')

        fixed_count = 0
        skipped_count = 0
        failed_count = 0

        for brand in brands_with_thumbnails:
            try:
                original_path = brand.thumbnail.path
                original_filename = os.path.basename(original_path)
                
                # 파일의 내용(바이너리 데이터)을 읽어옵니다.
                brand.thumbnail.open(mode='rb')
                file_content = brand.thumbnail.read()
                brand.thumbnail.close()

                # ✅ [핵심] 파일의 내용물을 직접 검사하여 진짜 타입을 알아냅니다.
                
                # --- 1. 이미 올바른 PNG 파일인 경우 ---
                if file_content.startswith(b'\x89PNG') and original_filename.lower().endswith('.png'):
                    self.stdout.write(self.style.SUCCESS(f'  [OK] "{brand.name}" is already a valid PNG. Skipping.'))
                    skipped_count += 1
                    continue

                # --- 2. 내용물은 진짜 SVG인 경우 -> PNG로 변환 ---
                elif file_content.strip().startswith(b'<svg'):
                    self.stdout.write(f'--- Fixing "{brand.name}" (SVG to PNG) ---')
                    png_content = cairosvg.svg2png(bytestring=file_content, output_height=200)
                    new_filename = os.path.splitext(original_filename)[0] + '.png'
                    brand.thumbnail.save(new_filename, ContentFile(png_content), save=True)
                    self.stdout.write(self.style.SUCCESS(f'  [+] Converted to {new_filename}'))
                    fixed_count += 1
                    
                # --- 3. 내용물은 WEBP인 경우 -> PNG로 변환 ---
                elif b'WEBP' in file_content[:16]:
                    self.stdout.write(f'--- Fixing "{brand.name}" (WEBP to PNG) ---')
                    img = Image.open(BytesIO(file_content)).convert("RGBA")
                    output_buffer = BytesIO()
                    img.save(output_buffer, format='PNG')
                    png_content = output_buffer.getvalue()
                    new_filename = os.path.splitext(original_filename)[0] + '.png'
                    brand.thumbnail.save(new_filename, ContentFile(png_content), save=True)
                    self.stdout.write(self.style.SUCCESS(f'  [+] Converted to {new_filename}'))
                    fixed_count += 1

                # --- 4. 기타 이미지(JPG, GIF 등)인 경우 -> PNG로 변환 ---
                else:
                    self.stdout.write(f'--- Fixing "{brand.name}" (Image to PNG) ---')
                    img = Image.open(BytesIO(file_content)).convert("RGBA")
                    output_buffer = BytesIO()
                    img.save(output_buffer, format='PNG')
                    png_content = output_buffer.getvalue()
                    new_filename = os.path.splitext(original_filename)[0] + '.png'
                    brand.thumbnail.save(new_filename, ContentFile(png_content), save=True)
                    self.stdout.write(self.style.SUCCESS(f'  [+] Converted to {new_filename}'))
                    fixed_count += 1

            except Exception as e:
                self.stderr.write(self.style.ERROR(f'  [!] Failed to fix "{brand.name}": {e}'))
                failed_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n--- Fixing complete! ---'))
        self.stdout.write(f'{fixed_count} thumbnails were fixed.')
        self.stdout.write(f'{skipped_count} thumbnails were already correct.')
        if failed_count > 0:
            self.stdout.write(self.style.WARNING(f'{failed_count} thumbnails failed to fix.'))