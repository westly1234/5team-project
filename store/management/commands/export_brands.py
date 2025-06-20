# store/management/commands/export_brands.py

import csv
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from store.models import Brand

class Command(BaseCommand):
    help = 'Export all brands from the Brand model to a CSV file'

    def handle(self, *args, **kwargs):
        # 데이터베이스에서 모든 브랜드 정보를 가져옵니다 (이름순으로 정렬).
        brands = Brand.objects.all().order_by('name')

        if not brands.exists():
            self.stdout.write(self.style.WARNING('No brands found in the database to export.'))
            return

        # 내보낼 CSV 파일의 경로와 이름을 지정합니다.
        # 기존 import 파일과 헷갈리지 않도록 'brands_exported.csv'로 저장합니다.
        file_path = os.path.join(settings.BASE_DIR, 'brands_exported.csv')

        try:
            # CSV 파일을 쓰기 모드로 엽니다.
            # encoding='utf-8-sig'는 엑셀에서 한글이 깨지지 않게 해주는 중요한 설정입니다.
            # newline=''은 CSV 파일에 불필요한 빈 줄이 생기는 것을 방지합니다.
            with open(file_path, mode='w', encoding='utf-8-sig', newline='') as csvfile:
                # CSV writer 객체를 생성합니다.
                writer = csv.writer(csvfile)

                # 1. CSV 파일의 헤더(첫 줄)를 작성합니다.
                writer.writerow(['브랜드명', '링크', '썸네일 경로'])

                # 2. 데이터베이스에서 가져온 각 브랜드 정보를 한 줄씩 CSV에 작성합니다.
                for brand in brands:
                    # 썸네일이 없는 경우를 대비해, 있으면 URL을, 없으면 빈 문자열을 가져옵니다.
                    thumbnail_url = brand.thumbnail.url if brand.thumbnail else ''
                    
                    writer.writerow([
                        brand.name,
                        brand.link,
                        thumbnail_url
                    ])

            # 작업 완료 메시지를 터미널에 출력합니다.
            self.stdout.write(self.style.SUCCESS(
                f'Successfully exported {brands.count()} brands to: {file_path}'
            ))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred: {e}'))