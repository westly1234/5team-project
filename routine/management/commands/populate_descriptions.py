# routine/management/commands/populate_descriptions.py

from django.core.management.base import BaseCommand
from routine.models import Exercise
# 위에서 만든 Helper 함수를 import 합니다.
from routine.views import populate_exercise_details_if_empty
import time

class Command(BaseCommand):
    help = 'Populates missing descriptions and precautions for all exercises using OpenAI API.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate exercise details...'))
        
        # 설명이 비어있는 운동만 대상으로 조회
        exercises_to_update = Exercise.objects.filter(description__isnull=True)
        
        if not exercises_to_update.exists():
            self.stdout.write(self.style.WARNING('No exercises with missing descriptions found.'))
            return

        total_count = exercises_to_update.count()
        self.stdout.write(f'Found {total_count} exercises to update.')

        for i, exercise in enumerate(exercises_to_update):
            self.stdout.write(f'({i+1}/{total_count}) Processing: {exercise.name}...')
            try:
                populate_exercise_details_if_empty(exercise)
                self.stdout.write(self.style.SUCCESS(f'  -> Successfully populated.'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  -> Failed to populate {exercise.name}: {e}'))
            
            # API 속도 제한을 피하기 위해 각 요청 사이에 약간의 딜레이 추가
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Finished populating all exercises.'))