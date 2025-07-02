from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from web.templatetags.custom_translate import t_lazy

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': t_lazy('이메일 주소')
        })
    )
    first_name = forms.CharField(
        label=t_lazy('이름 (별명)'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': t_lazy('이름 또는 별명')
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image', 'height', 'current_weight', 'target_weight', 'skeletal_muscle_mass', 'body_fat_mass']
        widgets = {
            'image': forms.FileInput(attrs={'style': 'display: none;', 'id': 'id_image'}),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': t_lazy('키 (cm)')
            }),
            'current_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': t_lazy('현재 체중 (kg)')
            }),
            'target_weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': t_lazy('목표 체중 (kg)')
            }),
            'skeletal_muscle_mass': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': t_lazy('골격근량 (kg)')
            }),
            'body_fat_mass': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': t_lazy('체지방량 (kg)')
            }),
        }
        labels = {
            'height': t_lazy('키'),
            'current_weight': t_lazy('현재 체중'),
            'target_weight': t_lazy('목표 체중'),
            'skeletal_muscle_mass': t_lazy('골격근량'),
            'body_fat_mass': t_lazy('체지방량'),
        }


# ✅ 아이디 찾기 폼
class FindUsernameForm(forms.Form):
    email = forms.EmailField(label=t_lazy('가입한 이메일'))

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError(t_lazy('해당 이메일로 가입된 계정이 없습니다.'))
        return email
    
class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label=t_lazy('이메일 주소'),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'class': 'form-control'})
    )

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label=t_lazy('새 비밀번호'),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    new_password2 = forms.CharField(
        label=t_lazy('새 비밀번호 확인'),
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
  
