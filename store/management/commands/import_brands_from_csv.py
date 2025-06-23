import csv
import os
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from store.models import Brand, BrandCategory, Tag

class Command(BaseCommand):
    help = 'Imports or updates brands, assigns categories, and auto-generates tags from a specified CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str, help='The path to the CSV file to import.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file_path']

        # 카테고리 정의 (코드: 표시 이름)
        CATEGORY_DEFINITIONS = {
            'APPAREL': '의류',
            'EQUIPMENT': '운동용품',
            'SUPPLEMENTS': '보충제',
            'ACCESSORIES': '잡화/악세사리',
        }

        # 카테고리 자동 분류를 위한 키워드 사전
        CATEGORY_KEYWORDS = {
            'APPAREL': [
                'adidas', 'aider', 'ardentsoul', 'bermuser', 'better than life', 'black monster fit', 
                'born to win', 'descente', 'dimito', 'dynafit', 'everlast', 'exhale', 'fcmm', 
                'freedom', 'gbro', 'goalstudio', 'hardyroar', 'hdex', 'hadex', 'hotsuit', 
                'jeleve', 'kolca', 'leaden', 'leste', 'levasse', 'limelight apparel', 'lornajane', 
                'macblacksports', 'malden', 'mcnsports', 'mihak', 'muscle armed', 'muscleguard', 
                'musinsa standard', 'nike', 'oneaim', 'overtia', 'physical garments', 'proesce', 
                'puma', 'reebok', 'rexy', 'rough athletic', 'skullpig', 'somefit', 'sportler', 
                'spyder', 'stiz', 'sumnfit', 'takeform', 'tesla', 'tolance', 'tomdeer', 
                'ufc sport', 'unbroken', 'underarmour', 'valiant', 'venkany', 'wavewear', 'waydn', 
                'wecandare', 'wildbros', 'williwaw studio', 'xexymix', 'xnazzy', '젝시믹스', 
                '안다르', '뮬라웨어', '스파이더', '언더아머', '나이키', '아디다스', 'apparel', 'wear'
            ],
            'EQUIPMENT': [
                'barbellworks', 'ergogear', 'fitboon', 'fitflex', 'gearx', 'harbinger', 'irunner', 
                'livepro', 'liveup', 'mcdavid', 'medinstory', 'mumusk', 'ninez', 'nubells', 'poder', 
                'ready4next', 'runtwo', 'senti', 'shield', 'shockabsorber', 'tapingtech', 'wrm',
                'the weight company', 'theraband', 'turtleback', 'uplounge', '로그', '쉬크', '하빈져', 
                '베르사그립', '보호대', 'gear', 'equipment', 'band', 'roller', 'mat', 'ufc sport'
            ],
            'SUPPLEMENTS': [
                'jambaekee', 'jungfood', 'neimlab', 'nutritionfactory', 'seanlee', '마이프로틴', 
                '옵티멈뉴트리션', '신타', '보충제', '프로틴', 'nutrition', 'supplements', 'protein'
            ],
            'ACCESSORIES': [
                '4monster', 'aleaf', 'ardu', 'ballop', 'batip', 'bluegrain', 'bronis', 'buff', 'bysec', 
                'divingspot', 'grayl', 'hugvone', 'instay', 'khaki grado', 'lofix', 'odeoueknit', 
                'peggynco', 'phermenon', 'pointfixe', 'rabdy', 'reactify', 'rvd', '블렌더보틀', 
                '쉐이커', '가방', '모자', '벨트', '양말', 'bag', 'cap', 'bottle', 'shaker', 'socks',
                'adidas', 'nike', 'puma', 'underarmour'
            ],
        }

        # 태그 자동 생성을 위한 키워드 사전
        TAG_KEYWORDS = {
            '가성비': ['fcmm', 'tesla', 'hdex', 'hadex', '가성비'],
            '프리미엄': ['gymshark', 'alphalete', 'darcsport', 'ryderwear', 'lululemon', 'spyder', '프리미엄'],
            '국산': ['hdex', 'xexymix', '젝시믹스', '안다르', '뮬라웨어', '국산'],
            '글로벌': ['nike', 'adidas', 'underarmour', 'gymshark', 'myprotein', 'optimumnutrition', '글로벌'],
            '디자인': ['gymshark', 'alphalete', 'darcsport', '디자인'],
            '기능성': ['nike', 'adidas', 'underarmour', 'spyder', 'descente', 'dynafit', 'hotsuit', 'tapingtech', 'wavewear', '기능성'],
            '초심자용': ['harbinger', 'everlast', 'tesla', '초보', '입문'],
            '전문가용': ['sbd', 'rogue', 'versa gripps', '전문가', '고급'],
            'WPI': ['wpi', '아이솔레이트'],
            '다이어트': ['다이어트', '저칼로리', '체지방'],
            '비건': ['비건', 'vegan', '식물성'],
        }
        
        start_time = time.time()
        self.stdout.write(self.style.SUCCESS("🚀 브랜드 데이터베이스 업데이트를 시작합니다..."))

        # 1. BrandCategory 객체들이 DB에 존재하는지 확인하고 없으면 생성
        self.stdout.write("1. 카테고리 정보를 확인 및 생성합니다...")
        for code, name in CATEGORY_DEFINITIONS.items():
            category, created = BrandCategory.objects.get_or_create(code=code, defaults={'name': name})
            if created:
                self.stdout.write(f"  - 카테고리 '{name}' 생성됨.")

        # 2. CSV 파일로부터 브랜드 정보를 읽고 카테고리 및 태그 할당
        self.stdout.write(f"2. '{csv_file_path}' 파일로부터 브랜드 정보를 임포트 및 재분류합니다...")
        
        updated_count = 0
        created_count = 0

        try:
            with transaction.atomic():
                with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
                    for row in csv.DictReader(csv_file):
                        brand_name = row.get('브랜드명')
                        if not brand_name:
                            self.stdout.write(self.style.WARNING("  - 브랜드명이 없는 행을 건너뜁니다."))
                            continue

                        brand, created = Brand.objects.get_or_create(name=brand_name)
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                        
                        # 링크 및 썸네일 정보 업데이트
                        brand.link = row.get('링크', '')
                        thumbnail_path = row.get('썸네일 경로', '')
                        if thumbnail_path:
                            brand.thumbnail = os.path.join('brand_thumbnails', os.path.basename(thumbnail_path))
                        
                        # 설명 필드가 있다면 업데이트 (태그 검색에 사용)
                        # brand.description = row.get('설명', brand.description)
                        
                        brand.save()

                        # 카테고리 할당 로직
                        found_category_codes = {
                            code for code, kw_list in CATEGORY_KEYWORDS.items() 
                            if any(kw in brand.name.lower() for kw in kw_list)
                        }
                        if found_category_codes:
                            categories_to_set = BrandCategory.objects.filter(code__in=found_category_codes)
                            brand.categories.set(categories_to_set)
                        else:
                            brand.categories.clear()

                        # 태그 할당 로직
                        found_tags = []
                        search_text = (brand.name + " " + brand.description).lower()
                        for tag_name, keywords in TAG_KEYWORDS.items():
                            if any(keyword in search_text for keyword in keywords):
                                tag, _ = Tag.objects.get_or_create(name=tag_name)
                                found_tags.append(tag)
                        
                        if found_tags:
                            brand.tags.set(found_tags)
                        else:
                            brand.tags.clear()

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"오류: 파일을 찾을 수 없습니다 - '{csv_file_path}'"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"작업 중 오류가 발생했습니다: {e}"))
            return

        end_time = time.time()
        duration = end_time - start_time

        self.stdout.write(self.style.SUCCESS("-" * 40))
        self.stdout.write(self.style.SUCCESS(f"✅ 모든 작업 완료! (총 소요 시간: {duration:.2f}초)"))
        self.stdout.write(f"  - 새로 생성된 브랜드: {created_count}개")
        self.stdout.write(f"  - 업데이트된 브랜드: {updated_count}개")