# store/management/commands/scrape_categories.py

import requests
from bs4 import BeautifulSoup
import time
import os
import re
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
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
from selenium.common.exceptions import TimeoutException

# SVG to PNG
import cairosvg

class Command(BaseCommand):
    help = 'The definitive scraper: Uses Selenium to categorize brands and download logos as PNG.'

    def handle(self, *args, **kwargs):
        # 키워드 목록
        CATEGORY_KEYWORDS = {
            'APPAREL': ['티셔츠', '반팔', '맨투맨', '후드', '셔츠', '니트', '스웨터', '팬츠', '바지', '데님', '조거', '슬랙스', '레깅스', '쇼츠', '재킷', '아우터', '점퍼', '코트', '패딩', '아노락', '바람막이', '언더웨어', '브라탑', '스포츠브라', '탑', '웨어'],
            'EQUIPMENT': ['덤벨', '바벨', '원판', '케틀벨', '그립', '스트랩', '벨트', '블럭', '매트', '요가', '필라테스', '폼롤러', '마사지', '밴드', '세라밴드', '풀업', '푸쉬업', '딥스', '철봉', '로프', '줄넘기', '런닝머신', '워킹패드'],
            'SUPPLEMENTS': ['프로틴', '단백질', '부스터', '보충제', 'BCAA', '아르기닌', '크레아틴', '비타민', '헬스', '푸드'],
            'ACCESSORIES': ['가방', '백팩', '모자', '캡', '양말', '삭스', '보틀', '물통', '쉐이커', '글러브', '장갑', '보호대', '무릎', '손목', '필터', '정수'],
        }

        # Selenium 옵션 설정
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        brands_to_process = Brand.objects.filter(Q(thumbnail__isnull=True) | Q(category='ETC'))
        if not brands_to_process.exists():
            self.stdout.write(self.style.SUCCESS('All brands are already processed.'))
            driver.quit()
            return

        self.stdout.write(f'Found {brands_to_process.count()} brands to process. Starting dynamic scraping...')
        
        processed_count = 0
        try:
            for brand in brands_to_process:
                self.stdout.write(f'--- Processing "{brand.name}" ---')
                try:
                    driver.get(brand.link)
                    
                    # ✅ [업그레이드] 상품 목록(.list-box) 또는 브랜드 설명(.brand_txt) 중 하나라도 나타나면 통과
                    try:
                        wait = WebDriverWait(driver, 7)
                        wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".list-box, .brand_txt")
                        ))
                    except TimeoutException:
                        self.stdout.write(self.style.WARNING(f'  [!] Key elements not found for "{brand.name}". Proceeding with what is available.'))

                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    needs_save = False

                    # 로고 이미지 스크레이핑
                    if not brand.thumbnail:
                        logo_img_tag = soup.find('img', src=re.compile(r'/brand/.*_logo_img/'))
                        if logo_img_tag and logo_img_tag.get('src'):
                            logo_url = logo_img_tag['src']
                            if logo_url.startswith('//'): logo_url = 'https:' + logo_url
                            
                            img_response = requests.get(logo_url, timeout=10)
                            if img_response.status_code == 200:
                                file_content = img_response.content
                                original_filename = os.path.basename(urlparse(logo_url).path)
                                
                                if original_filename.lower().endswith('.svg'):
                                    try:
                                        png_content = cairosvg.svg2png(bytestring=file_content, output_height=200)
                                        file_content = png_content
                                        original_filename = os.path.splitext(original_filename)[0] + '.png'
                                    except Exception as e:
                                        self.stderr.write(self.style.ERROR(f'  [!] SVG conversion failed: {e}'))
                                
                                brand.thumbnail.save(original_filename, ContentFile(file_content), save=False)
                                needs_save = True
                                self.stdout.write(self.style.SUCCESS(f'  [+] Logo found and saved: {original_filename}'))

                    # 카테고리 분류
                    if brand.category == 'ETC':
                        # ✅ [업그레이드] 분석할 텍스트를 여러 군데에서 안전하게 가져옵니다.
                        list_box = soup.find('div', class_='list-box')
                        description_box = soup.find('p', class_='brand_txt')
                        
                        product_text = list_box.get_text(separator=' ', strip=True) if list_box else ''
                        description_text = description_box.get_text(separator=' ', strip=True) if description_box else ''
                        
                        # 두 텍스트를 합쳐서 분석의 정확도를 높입니다.
                        combined_text = product_text + " " + description_text
                        
                        assigned = False
                        if combined_text.strip():
                            for category, keywords in CATEGORY_KEYWORDS.items():
                                for keyword in keywords:
                                    if keyword in combined_text:
                                        brand.category = category
                                        needs_save = True
                                        self.stdout.write(self.style.SUCCESS(f'  [+] Category assigned: {brand.get_category_display()}'))
                                        assigned = True
                                        break
                                if assigned: break
                        if not assigned: self.stdout.write(self.style.WARNING('  [-] Could not determine category.'))

                    if needs_save:
                        brand.save()
                        processed_count += 1
                    else:
                        self.stdout.write('  [-] No changes needed.')
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  [!] An error occurred during "{brand.name}" processing: {e}'))
                
                time.sleep(1) # 서버 부하 감소를 위한 1초 대기
        finally:
            driver.quit()

        self.stdout.write(self.style.SUCCESS(f'\n--- Scraping complete! ---'))
        self.stdout.write(f'{processed_count} brand records were updated.')