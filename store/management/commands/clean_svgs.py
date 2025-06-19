# store/management/commands/clean_svgs.py

import os
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Deletes all .svg files from the brand_thumbnails media folder.'

    def handle(self, *args, **kwargs):
        # 썸네일이 저장되는 폴더의 전체 경로를 가져옵니다.
        # settings.MEDIA_ROOT는 'media/' 폴더를 가리킵니다.
        thumbnail_dir = os.path.join(settings.MEDIA_ROOT, 'brand_thumbnails')

        if not os.path.isdir(thumbnail_dir):
            self.stdout.write(self.style.WARNING(f'Directory not found: {thumbnail_dir}'))
            return

        self.stdout.write(f'Searching for .svg files in: {thumbnail_dir}')

        deleted_count = 0
        # 폴더 안의 모든 파일을 순회합니다.
        for filename in os.listdir(thumbnail_dir):
            # 파일 이름이 .svg로 끝나는 경우에만
            if filename.lower().endswith('.svg'):
                file_path = os.path.join(thumbnail_dir, filename)
                try:
                    # 파일을 삭제합니다.
                    os.remove(file_path)
                    self.stdout.write(self.style.SUCCESS(f'  [DELETED] {filename}'))
                    deleted_count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  [FAILED] Could not delete {filename}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\n--- Cleanup complete! ---'))
        self.stdout.write(f'{deleted_count} .svg files were deleted.')