import os
from django.conf import settings
from django.utils import translation

def load_prompt(prompt_name, context=None):
    """
    store/prompts/ 폴더에서 특정 프롬프트 파일을 현재 언어에 맞게 읽어옵니다.
    
    - prompt_name: 프롬프트 파일의 기본 이름 (예: 'brand_description')
    - context: 프롬프트 내용의 변수({변수명})를 채우기 위한 딕셔너리
    """
    # 현재 활성화된 언어 코드 가져오기 (예: 'ko', 'en')
    current_language = translation.get_language()
    
    # store 앱 내의 prompts 폴더 경로 설정
    # 예: /path/to/project/store/prompts/brand_description_en.txt
    file_path = settings.BASE_DIR / 'store' / 'prompts' / f'{prompt_name}_{current_language}.txt'

    # 만약 현재 언어의 프롬프트 파일이 없다면, 기본 언어인 한국어 프롬프트로 대체
    if not os.path.exists(file_path):
        file_path = settings.BASE_DIR / 'store' / 'prompts' / f'{prompt_name}_ko.txt'
        # 한국어 프롬프트 파일도 없으면 에러 발생
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Default prompt file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    # context가 제공되면, 프롬프트 내용의 변수를 실제 값으로 치환
    if context:
        return prompt_template.format(**context)
        
    return prompt_template