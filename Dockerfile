# Python 기반 이미지 사용
FROM python:3.11-slim

# 환경변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# requirements 설치
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 프로젝트 전체 복사
COPY . .

# static 파일 수집
RUN python manage.py collectstatic --noinput

# 포트 지정
EXPOSE 8000

# Gunicorn으로 서버 실행
CMD gunicorn config.wsgi:application --bind 0.0.0.0:8000
