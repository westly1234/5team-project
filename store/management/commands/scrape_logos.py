# store/management/commands/scrape_logos.py

import requests
import time
import os
import re
from urllib.parse import urlparse

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from store.models import Brand

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import cairosvg

class Command(BaseCommand):
    help = 'Scrapes Musinsa brand pages to find, download, and save brand logos as PNG.'

    def handle(self, *args, **kwargs):
        # Selenium 옵션 설정
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # ✅ 썸네일이 없는 브랜드만 대상으로 작업합니다.
        brands_to_process = Brand.objects.filter(thumbnail__isnull=True)
        if not brands_to_process.exists():
            self.stdout.write(self.style.SUCCESS('All brand logos are already downloaded.'))
            driver.quit()
            return

        self.stdout.write(f'Found {brands_to_process.count()} brands without logos. Starting scraping...')
        
        processed_count = 0
        try:
            for brand in brands_to_process:
                self.stdout.write(f'--- Processing "{brand.name}" ---')
                try:
                    driver.get(brand.link)
                    
                    # 페이지가 로드될 때까지 최소한의 대기
                    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    
                    # ✅ [핵심] 정규표현식을 사용하여 로고 이미지 태그를 정확히 찾아냅니다.
                    logo_img_element = driver.find_element(By.CSS_SELECTOR, "img[src*='/brand/white_logo_img/']")
                    
                    if logo_img_element:
                        logo_url = logo_img_element.get_attribute('src')
                        if logo_url.startswith('//'): logo_url = 'https:' + logo_url
                        
                        # 이미지 다운로드
                        img_response = requests.get(logo_url, timeout=10)
                        if img_response.status_code == 200:
                            file_content = img_response.content
                            original_filename = os.path.basename(urlparse(logo_url).path)
                            
                            # SVG인 경우 PNG로 변환
                            if original_filename.lower().endswith('.svg'):
                                try:
                                    png_content = cairosvg.svg2png(bytestring=file_content, output_height=200)
                                    file_content = png_content
                                    original_filename = os.path.splitext(original_filename)[0] + '.png'
                                except Exception as e:
                                    self.stderr.write(self.style.ERROR(f'  [!] SVG conversion failed: {e}'))
                            
                            # DB에 저장
                            brand.thumbnail.save(original_filename, ContentFile(file_content), save=True)
                            self.stdout.write(self.style.SUCCESS(f'  [+] Logo for "{brand.name}" saved as {original_filename}'))
                            processed_count += 1
                        else:
                            self.stdout.write(self.style.WARNING(f'  [-] Logo found, but could not download. Status: {img_response.status_code}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'  [-] Logo image tag not found for "{brand.name}"'))

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f'  [!] An error occurred during "{brand.name}" processing: {e}'))
                
                time.sleep(0.5) # 서버 부하 감소를 위한 예의
        finally:
            driver.quit()

        self.stdout.write(self.style.SUCCESS(f'\n--- Scraping complete! ---'))
        self.stdout.write(f'{processed_count} logos were downloaded and saved.')