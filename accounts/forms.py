from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']  # email 저장
        if commit:
            user.save()
        return user
    

# accounts/forms.py

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        # ✅ 위젯을 사용하여 HTML 속성 직접 지정
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': '이메일 주소'
        })
    )
    first_name = forms.CharField(
        label='이름 (별명)',
        required=False, # 필수 항목이 아닐 경우
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '이름 또는 별명'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        # ✅ fields 리스트에 추가
        fields = ['image', 'height', 'current_weight', 'target_weight', 'skeletal_muscle_mass', 'body_fat_mass']
        
        widgets = {
            'image': forms.FileInput(attrs={'style': 'display: none;', 'id': 'id_image'}),
            'height': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '키 (cm)'
            }),
            'current_weight': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '현재 체중 (kg)'
            }),
            'target_weight': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': '목표 체중 (kg)'
            }),
            # ✅ 새로 추가된 필드들의 위젯 설정
            'skeletal_muscle_mass': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '골격근량 (kg)'
            }),
            'body_fat_mass': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '체지방량 (kg)'
            }),
        }
        labels = {
            'height': '키',
            'current_weight': '현재 체중',
            'target_weight': '목표 체중',
            # ✅ 새로 추가된 필드들의 라벨 설정
            'skeletal_muscle_mass': '골격근량',
            'body_fat_mass': '체지방량',
        }