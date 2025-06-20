from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-a^3=vq=*a+u*)sagi%5kr9^$gmgl379y5)9q=a%_f*b6$9)$vx'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['192.168.0.205', 'localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "accounts.apps.AccountsConfig",
    'achievements',
    'web.apps.WebConfig',
    'music',
    'place',
    'routine',
    'diet',
    'chatbot',
    'store',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        
        # ✅ [수정됨] 템플릿을 찾는 기본 폴더를 프로젝트 최상위의 'templates' 폴더로 지정합니다.
        # 이렇게 하면 Django가 web/templates, music/templates 등을 더 안정적으로 찾을 수 있습니다.
        # 만약 프로젝트 최상위에 templates 폴더가 없다면, web/templates/web, music/templates/music 과 같은
        # 앱별 템플릿 구조를 더 잘 인식하게 됩니다.
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        
        'APP_DIRS': True, # 이 설정은 각 앱 내부의 'templates' 폴더를 자동으로 찾게 해줍니다.
        
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "assets",
    #BASE_DIR / "mysite" / "web" / "templates" / "web" / "public" # 수정된 부분
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 로그인 및 로그아웃 관련 URL 설정
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Gmail SMTP 서버 주소
EMAIL_PORT = 587               # Gmail SMTP 포트 (TLS 용)
EMAIL_USE_TLS = True           # TLS (전송 계층 보안) 사용
EMAIL_HOST_USER = 'tkfkd2661@gmail.com'  # 본인의 Gmail 주소 (발신자 주소)
EMAIL_HOST_PASSWORD = 'rdjtiuampolmrqgp'   # 위에서 생성한 16자리 앱 비밀번호

# 이메일 발송 시 기본 "보낸 사람"으로 표시될 주소 (보통 EMAIL_HOST_USER와 동일하게 설정)
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

load_dotenv()

# API KEYS
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
KAKAO_MAP_API_KEY = os.getenv('KAKAO_MAP_API_KEY')

# config/settings.py 맨 아래에 추가

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 챗봇 설정 (Chatbot Settings)
# =============================================================================
# 벡터 DB 경로 (프로젝트 루트에 'project_data' 폴더를 만든다고 가정)
VECTORSTORE_PATH = os.path.join(BASE_DIR, 'project_data', 'vectorstore_food_and_healthy')

# 임베딩 모델 이름
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

# 임시 이미지 저장 경로 (프로젝트 루트의 'media' 폴더 내에 'temp_images' 폴더를 사용)
TEMP_IMAGE_DIR = os.path.join(MEDIA_ROOT, 'temp_images')

# TEMP_IMAGE_DIR이 존재하지 않으면 생성
os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)