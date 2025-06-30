import os
import re
import json
from pathlib import Path
from django.core.management.base import BaseCommand

# BaseCommand를 상속받는 Command 클래스 정의
class Command(BaseCommand):
    help = 'ko.json 파일을 기반으로 HTML 템플릿의 한국어 텍스트를 Django 템플릿 태그로 변환합니다.'

    def handle(self, *args, **kwargs):
        # --- 설정 ---
        BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
        TEMPLATE_DIRS = [
            BASE_DIR / 'web' / 'templates',
            BASE_DIR / 'accounts' / 'templates',
            BASE_DIR / 'chatbot' / 'templates',
            BASE_DIR / 'diet' / 'templates',
            BASE_DIR / 'edit' / 'templates',
            BASE_DIR / 'music' / 'templates',
            BASE_DIR / 'place' / 'templates',
            BASE_DIR / 'routine' / 'templates',
            BASE_DIR / 'store' / 'templates',
        ]
        KOREAN_JSON_PATH = BASE_DIR / 'locales' / 'ko.json'
        # --- 설정 끝 ---

        self.stdout.write("="*50)
        self.stdout.write("ko.json 기반 Django 템플릿 변환 스크립트 (v3)를 시작합니다.")
        
        value_to_key_map = self.load_korean_json(KOREAN_JSON_PATH)
        if not value_to_key_map:
            return
        
        sorted_texts = sorted(value_to_key_map.keys(), key=len, reverse=True)
        combined_regex = self.create_regex_from_keys(sorted_texts)

        for template_dir in TEMPLATE_DIRS:
            if not template_dir.is_dir():
                self.stdout.write(self.style.WARNING(f"  - 경고: '{template_dir}' 폴더를 찾을 수 없습니다. 건너뜁니다."))
                continue
                
            self.stdout.write("\n" + "="*50)
            self.stdout.write(f"🔍 '{template_dir}' 폴더에서 HTML 파일을 찾습니다...")
            for root, _, files in os.walk(template_dir):
                for filename in files:
                    if filename.endswith(".html"):
                        self.process_file(Path(root) / filename, value_to_key_map, combined_regex)

        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS("모든 작업이 완료되었습니다."))

    def load_korean_json(self, path):
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"❌ 오류: '{path}' 파일을 찾을 수 없습니다. 경로를 확인해주세요."))
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        value_to_key_map = {value: key for key, value in data.items()}
        self.stdout.write(self.style.SUCCESS(f"✅ '{path}' 로드 완료. {len(value_to_key_map)}개의 번역 항목을 찾았습니다."))
        return value_to_key_map

    def create_regex_from_keys(self, text_list):
        escaped_texts = [re.escape(text) for text in text_list]
        pattern = r'>\s*(' + '|'.join(escaped_texts) + r')\s*<'
        return re.compile(pattern)

    def process_file(self, file_path, value_to_key_map, regex_pattern):
        self.stdout.write(f"🔄 처리 중: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            def replacement_func(match):
                found_text = match.group(1).strip()
                if found_text in value_to_key_map:
                    key = value_to_key_map[found_text]
                    if "'" in key or '"' in key:
                        self.stdout.write(self.style.WARNING(f"  ⚠️ 경고: 키 '{key}'에 따옴표가 포함되어 있어 건너뜁니다. 수동으로 처리해주세요."))
                        return match.group(0)
                    
                    # [수정된 부분] f-string 안에서 중괄호를 문자로 사용하기 위해 두 번씩 사용
                    return f'>{{% t "{key}" %}}<'
                
                return match.group(0)

            has_load_tag = re.search(r'{%\s*load\s+.*custom_translate.*%}', content)
            
            new_content, count = regex_pattern.subn(replacement_func, content)
            
            if count > 0:
                if not has_load_tag:
                    load_tag = '{% load static i18n custom_translate %}\n'
                    if new_content.lstrip().startswith(('<!DOCTYPE', '<html')):
                        match = re.search(r'<\!DOCTYPE|<html', new_content, re.IGNORECASE)
                        if match:
                            insert_pos = match.start()
                            new_content = new_content[:insert_pos] + load_tag + new_content[insert_pos:]
                        else:
                            new_content = load_tag + new_content
                    else:
                        new_content = load_tag + new_content
                    self.stdout.write(self.style.SUCCESS(f"  ✨ {{% load custom_translate %}} 태그를 추가했습니다."))

                self.stdout.write(self.style.SUCCESS(f"  ✅ {count}개의 항목을 변환했습니다. 파일을 저장합니다."))
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            else:
                self.stdout.write("  - 변환할 항목이 없습니다.")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"  ❌ 오류 발생: {file_path} - {e}"))