import os
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Deletes temporary chat images older than 7 days.'

    def handle(self, *args, **options):
        # 임시 이미지 폴더 경로를 settings.py에서 가져옴
        temp_dir = getattr(settings, 'TEMP_IMAGE_DIR', None)

        if not temp_dir or not os.path.isdir(temp_dir):
            self.stdout.write(self.style.ERROR(f"TEMP_IMAGE_DIR이 설정되지 않았거나, '{temp_dir}' 폴더를 찾을 수 없습니다."))
            return

        self.stdout.write(f"'{temp_dir}' 폴더에서 7일 이상된 임시 파일 정리를 시작합니다...")

        # 7일의 기준 시간 설정 (현재 시간으로부터 7일 전)
        seven_days_ago = time.time() - timedelta(days=7).total_seconds()
        files_deleted = 0
        
        # 폴더 내의 모든 파일을 순회
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            
            # 파일일 경우에만 처리
            if os.path.isfile(file_path):
                try:
                    # 파일의 최종 수정 시간을 가져옴
                    file_mod_time = os.path.getmtime(file_path)
                    
                    # 파일의 수정 시간이 7일보다 오래되었다면 삭제
                    if file_mod_time < seven_days_ago:
                        os.remove(file_path)
                        self.stdout.write(f"  - 삭제: {filename}")
                        files_deleted += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"'{filename}' 파일 처리 중 오류 발생: {e}"))

        self.stdout.write(self.style.SUCCESS(f"총 {files_deleted}개의 오래된 임시 파일을 성공적으로 삭제했습니다."))