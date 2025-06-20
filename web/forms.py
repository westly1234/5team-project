# your_app_name/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User # 기본 User 모델 사용 시

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text='선택 사항입니다. 비밀번호 재설정 등에 사용될 수 있습니다.') # 이메일 필드 추가 (선택 사항)

    class Meta(UserCreationForm.Meta):
        model = User # 기본 User 모델을 사용한다고 가정
        fields = UserCreationForm.Meta.fields + ('email',) # 기존 필드에 이메일 필드 추가
        # 만약 username, password1, password2 외에 다른 필드 순서를 원하거나,
        # email 필드를 필수 필드로 만들고 싶다면 fields를 직접 정의할 수 있습니다.
        # fields = ('username', 'email', 'password1', 'password2')

    # 필요하다면 clean_email, clean_username 등의 유효성 검사 메소드를 추가할 수 있습니다.
    # def clean_email(self):
    #     email = self.cleaned_data.get('email')
    #     if email and User.objects.filter(email=email).exists():
    #         raise forms.ValidationError("이미 사용 중인 이메일입니다.")
    #     return email