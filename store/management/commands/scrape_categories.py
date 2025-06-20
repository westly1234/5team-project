# store/management/commands/scrape_categories.py

import time
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db.models import Q
from store.models import Brand

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.page_load_strategy import PageLoadStrategy

class Command(BaseCommand):
    help = 'Scrapes Musinsa brand pages to assign categories and fill in descriptions with robust settings.'

    def handle(self, *args, **kwargs):
        CATEGORY_KEYWORDS = {
            'NUTRITION': ['프로틴', '단백질', '보충제', 'BCAA', '아르기닌', '크레아틴', '부스터', '비타민', '영양', '푸드', '식품', '헬스'],
            'EQUIPMENT': ['덤벨', '바벨', '원판', '케틀벨', '그립', '스트랩', '벨트', '블럭', '매트', '요가', '필라테스', '폼롤러', '마사지', '밴드', '풀업', '푸쉬업', '딥스', '철봉', '로프', '줄넘기', '런닝머신', '워킹패드', '기구', '피트니스', '운동'],
            'CLOTHING': ['티셔츠', '맨투맨', '후드', '셔츠', '니트', '팬츠', '바지', '레깅스', '쇼츠', '재킷', '아우터', '점퍼', '코트', '패딩', '아노락', '언더웨어', '브라탑', '스포츠브라', '웨어', '의류', '탑', '삭스', '양말'],
            'ACCESSORIES': ['가방', '백팩', '모자', '캡', '보틀', '물통', '쉐이커', '글러브', '장갑', '보호대', '무릎', '손목', '타월', '스포츠'],
        }

        # --- Selenium 옵션 강화 ---
        options = Options()
        # ✅ [개선] 페이지 로드 전략 변경: 'eager'는 DOM 트리만 완성되면 다음으로 넘어감 (이미지 등 리소스 로딩은 기다리지 않음)
        options.page_load_strategy = PageLoadStrategy.EAGER
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument("--enable-unsafe-swiftshader")
        # ✅ [개선] 시스템 리소스 부족에 대응
        options.add_argument("--disable-dev-shm-usage") 
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
        
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            # ✅ [개선] 페이지 로딩 타임아웃 설정 (30초)
            driver.set_page_load_timeout(30)
        except WebDriverException as e:
            self.stderr.write(self.style.ERROR(f"WebDriver 초기화 실패: {e}"))
            return

        brands_to_process = Brand.objects.filter(
            Q(category='ETC') | Q(description='')
        ).order_by('name')
        
        if not brands_to_process.exists():
            self.stdout.write(self.style.SUCCESS('모든 브랜드가 이미 처리되었습니다.'))
            driver.quit()
            return

        self.stdout.write(f'{brands_to_process.count()}개의 브랜드를 처리합니다. 스크레이핑을 시작합니다...')
        
        processed_count = 0
        failed_count = 0
        try:
            for brand in brands_to_process:
                self.stdout.write(f'--- 처리 중: "{brand.name}" ---')
                needs_save = False
                try:
                    driver.get(brand.link)
                    
                    # ✅ [개선] 더 단순하고 확실한 대기 조건: <body> 태그가 나타날 때까지 기다림
                    # 대기 시간도 15초로 증가
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    soup = BeautifulSoup(driver.page_source, 'html.parser')

                    # --- 텍스트 수집 및 처리 로직은 이전과 동일 ---
                    text_sources = []
                    if not brand.description:
                        brand_desc_tag = soup.select_one('.brand_txt, .brand-header__description')
                        if brand_desc_tag:
                            description_content = brand_desc_tag.get_text(strip=True)
                            if description_content:
                                brand.description = description_content[:200]
                                brand.detailed_description = description_content
                                text_sources.append(description_content)
                                needs_save = True
                                self.stdout.write(self.style.SUCCESS(f'  [+] 설명 추가됨.'))
                        else:
                            self.stdout.write(self.style.WARNING('  [-] 설명 태그를 찾을 수 없음.'))
                    
                    if brand.category == 'ETC':
                        product_infos = soup.select('.article_info')
                        product_texts = []
                        for info in product_infos:
                            title = info.select_one('.item_title a')
                            desc = info.select_one('p.product_article_contents')
                            if title: product_texts.append(title.get_text(strip=True))
                            if desc: product_texts.append(desc.get_text(strip=True))
                        
                        if product_texts:
                            text_sources.append(' '.join(product_texts))

                        combined_text = ' '.join(text_sources)
                        assigned = False
                        if combined_text:
                            for category, keywords in CATEGORY_KEYWORDS.items():
                                if any(keyword in combined_text for keyword in keywords):
                                    brand.category = category
                                    needs_save = True
                                    self.stdout.write(self.style.SUCCESS(f'  [+] 카테고리 할당됨: {brand.get_category_display()}'))
                                    assigned = True
                                    break
                        if not assigned:
                            self.stdout.write(self.style.WARNING('  [-] 카테고리를 특정할 수 없음.'))
                    
                    if needs_save:
                        brand.save()
                        processed_count += 1
                    else:
                        self.stdout.write('  [-] 변경 사항 없음.')
                
                except TimeoutException:
                    self.stderr.write(self.style.ERROR(f'  [!] "{brand.name}" 페이지 로딩/처리 시간 초과. 건너뜁니다.'))
                    failed_count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  [!] "{brand.name}" 처리 중 예외 발생: {e}'))
                    failed_count += 1
                
                time.sleep(1) # 부하 감소를 위해 1초 대기

        finally:
            driver.quit()

        self.stdout.write(self.style.SUCCESS(f'\n--- 스크레이핑 완료! ---'))
        self.stdout.write(f'  - 성공: {processed_count}개 브랜드 업데이트됨.')
        self.stdout.write(f'  - 실패/건너뜀: {failed_count}개.')