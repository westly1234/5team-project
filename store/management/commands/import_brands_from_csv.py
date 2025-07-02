import csv
import os
import time
import json
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from store.models import Brand, BrandCategory, Tag
from openai import OpenAI

try:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    AI_ENABLED = True
except Exception:
    AI_ENABLED = False

class Command(BaseCommand):
    help = 'Imports brands from CSV, and uses AI to classify categories and tags.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file_path', type=str, help='The path to the CSV file.')
        parser.add_argument(
            '--no-ai',
            action='store_true',
            help='Skip AI-based classification and use keyword matching only.',
        )

    def get_ai_classification(self, brand_name, brand_link):
        """AI에게 브랜드 정보를 주고 카테고리와 태그를 분류받는 함수"""
        if not AI_ENABLED:
            return None

        categories_info = "의류, 운동용품, 보충제, 잡화/액세서리"
        tags_info = "가성비, 프리미엄, 국산, 글로벌, 기능성, 초심자용, 전문가용, WPI, 다이어트, 비건"

        prompt = f"""
        당신은 피트니스 및 헬스 용품 시장 분석 전문가입니다. 주어진 브랜드 이름과 링크를 보고, 아래 규칙에 따라 해당 브랜드를 분석하고 분류해주세요.

        [분류 기준]
        1. 카테고리 (아래 중 가장 적합한 것을 모두 선택): {categories_info}
        2. 태그 (아래 중 적합한 것을 모두 선택, 목록에 없다면 새로 제안 가능): {tags_info}

        [분석 대상 브랜드]
        - 이름: "{brand_name}"
        - 웹사이트 링크: {brand_link if brand_link else "제공되지 않음"}

        [출력 규칙]
        - 반드시 아래와 같은 JSON 형식으로만 답변해주세요. 다른 설명은 절대 추가하지 마세요.
        - 만약 링크가 없다면, 브랜드 이름만으로 최대한 유추해주세요.
        - 확실하지 않으면 빈 리스트 `[]`를 반환하세요.

        {{
          "categories": ["카테고리1", "카테고리2"],
          "tags": ["태그1", "태그2", "태그3"]
        }}
        """
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            result_json = json.loads(response.choices[0].message.content)
            
            if isinstance(result_json, dict) and 'categories' in result_json and 'tags' in result_json:
                return result_json
            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n  - AI 분석 중 오류 발생 ({brand_name}): {e}"))
            return None

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file_path = options['csv_file_path']
        use_ai = not options['no_ai'] and AI_ENABLED

        # --- 기본 카테고리 및 태그 생성 ---
        CATEGORY_DEFINITIONS = {'APPAREL': '의류', 'EQUIPMENT': '운동용품', 'SUPPLEMENTS': '보충제', 'ACCESSORIES': '잡화/액세서리'}
        TAG_NAMES = ['가성비', '프리미엄', '국산', '글로벌', '기능성', '초심자용', '전문가용', 'WPI', '다이어트', '비건']
        
        self.stdout.write("1. 기본 카테고리 및 태그 정보를 확인 및 생성합니다...")
        for code, name in CATEGORY_DEFINITIONS.items():
            BrandCategory.objects.get_or_create(code=code, defaults={'name_ko': name, 'name': name})
        for tag_name in TAG_NAMES:
            Tag.objects.get_or_create(name_ko=tag_name, defaults={'name': tag_name})
        self.stdout.write("  - 기본 카테고리 및 태그 준비 완료.")

        start_time = time.time()
        self.stdout.write(f"🚀 브랜드 임포트를 시작합니다... (AI 분석: {'활성화' if use_ai else '비활성화'})")

        # --- CSV 처리 ---
        try:
            with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = list(csv.DictReader(csv_file))
                total_rows = len(reader)
                
                for i, row in enumerate(reader):
                    brand_name = row.get('브랜드명')
                    brand_link = row.get('링크', '')

                    if not brand_name:
                        continue

                    brand, created = Brand.objects.get_or_create(name=brand_name)
                    
                    if use_ai:
                        self.stdout.write(f"\n[{i+1}/{total_rows}] 🧠 AI가 '{brand_name}' 브랜드를 분석 중입니다...")
                        
                        classification = self.get_ai_classification(brand.name, brand_link)
                        
                        if classification:
                            # AI가 분류한 카테고리 할당
                            cat_names = classification.get('categories', [])
                            if cat_names:
                                categories_to_set = BrandCategory.objects.filter(name_ko__in=cat_names)
                                brand.categories.set(categories_to_set)
                            
                            # --- ✨ [핵심 수정] AI가 반환한 태그 처리 로직 ---
                            tag_names = classification.get('tags', [])
                            tags_to_set = []
                            if tag_names:
                                for tag_name in tag_names:
                                    # 태그가 없으면 새로 생성하고, 있으면 가져옵니다.
                                    tag, created = Tag.objects.update_or_create(
                                        name_ko=tag_name,
                                        defaults={'name': tag_name} # 새로 생성 시 원본 name 필드도 채움
                                    )
                                    if created:
                                        self.stdout.write(self.style.SUCCESS(f"  - ✨ AI가 제안한 새 태그 생성: '{tag_name}'"))
                                    tags_to_set.append(tag)
                                
                                brand.tags.set(tags_to_set)

                            self.stdout.write(self.style.SUCCESS(f"  - AI 분석 완료: 카테고리 {cat_names}, 태그 {tag_names}"))
                            time.sleep(1)
                        else:
                            self.stdout.write(self.style.WARNING(f"  - AI 분석에 실패했거나 결과가 없습니다."))

                    # 나머지 정보 업데이트 및 저장
                    brand.link = brand_link
                    thumbnail_path = row.get('썸네일 경로', '')
                    if thumbnail_path:
                        brand.thumbnail = os.path.join('brand_thumbnails', os.path.basename(thumbnail_path))
                    brand.save()
        
        except FileNotFoundError:
            # ... (이하 동일)
            self.stderr.write(self.style.ERROR(f"오류: 파일을 찾을 수 없습니다 - '{csv_file_path}'"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"작업 중 오류가 발생했습니다: {e}"))
            raise e

        duration = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"\n✅ 모든 작업 완료! (총 소요 시간: {duration:.2f}초)"))