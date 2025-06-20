from django import forms
from .models import Meal

class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        # 사용자에게 입력받을 필드
        fields = ['image', 'text_input']
        
        # 각 필드를 HTML에서 어떻게 보여줄지 설정
        widgets = {
            'text_input': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': '먹은 음식에 대해 최대한 자세히 적어주세요.\n예: 흰 쌀밥 한 공기, 김치찌개, 계란후라이 1개',
                'class': 'w-full bg-gray-900 border border-gray-600 rounded-lg p-3 text-white focus:ring-blue-500 focus:border-blue-500'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-500/20 file:text-blue-300 hover:file:bg-blue-500/30'
            }),
        }
        
        # 필드의 라벨 텍스트 설정
        labels = {
            'image': '음식 사진 업로드',
            'text_input': '텍스트로 작성하기'
        }