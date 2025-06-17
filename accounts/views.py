from .forms import CustomUserCreationForm
from django.shortcuts import render, redirect
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from django.http import HttpRequest, JsonResponse
from django.core.mail import EmailMultiAlternatives
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from web.models import HealthSurvey
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm, ProfileUpdateForm
from .models import Profile 
from .models import Profile, BodyCompositionRecord


def signup(request: HttpRequest):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # 이메일 인증 전까지 비활성 상태로 설정
            user.save()  # ✅ 먼저 저장해서 user.id 생성

            survey_data = request.session.get('survey_data_temp')
            if survey_data:
                print(f"Processing survey data for user {user.email}: {survey_data}")
                try:
                    health_survey_instance = HealthSurvey(
                        blood_type=survey_data.get('blood_type', ''),
                        allergy=survey_data.get('allergy', []),
                        allergy_details=survey_data.get('allergy_details', ''),
                        chronic_disease=survey_data.get('chronic_disease', []),
                        chronic_disease_details=survey_data.get('chronic_disease_details', ''),
                        surgery_history=survey_data.get('surgery_history', ''),
                        current_medication=survey_data.get('current_medication', ''),
                        supplements=survey_data.get('supplements', ''),
                        smoking_status=survey_data.get('smoking_status', ''),
                        smoking_period=survey_data.get('smoking_period'),
                        smoking_amount=survey_data.get('smoking_amount'),
                        drinking_frequency=survey_data.get('drinking_frequency', ''),
                        drinking_amount=survey_data.get('drinking_amount', ''),
                        family_history=survey_data.get('family_history', []),
                        family_history_details=survey_data.get('family_history_details', ''),
                        user=user  # ✅ FK 연결 (user는 이미 save됨)
                    )
                    health_survey_instance.save()
                    print(f"HealthSurvey for {user.email} created and linked.")

                    if 'survey_data_temp' in request.session:
                        del request.session['survey_data_temp']
                        print("Temporary survey data deleted from session.")

                except Exception as e:
                    print(f"Error creating or saving HealthSurvey: {e}")

            # 이메일 인증 링크 생성
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            activation_link = request.build_absolute_uri(f"/accounts/activate/{uid}/{token}/")

            subject = "이메일 인증을 완료해주세요"
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [user.email]
            text_content = f"다음 링크를 클릭해서 인증을 완료해주세요: {activation_link}"
            html_content = render_to_string('accounts/activation_email.html', {
                'user': user,
                'activation_link': activation_link,
                'site_name': 'Your Family',
                'request': request,
            })
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            try:
                msg.send()
            except Exception as e:
                print(f"Email sending failed: {e}")

            return render(request, 'accounts/check_email.html')

        else:
            print("Signup form errors:", form.errors)
            context = {
                'form': form,
                'user_type_is_normal': True,
                'survey_completed': True
            }
            return render(request, 'accounts/signup.html', context)

    else:
        form = CustomUserCreationForm()
        return render(request, 'accounts/signup.html', {'form': form})



def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'accounts/activation.html')
    else:
        return render(request, 'accounts/activation_failed.html')


@require_POST
@csrf_exempt  # ❗개발 중 테스트용 — 실서비스에서는 반드시 제거하고 JS에서 CSRF 헤더 추가
def save_survey_view(request):
    try:
        survey_data = json.loads(request.body.decode('utf-8'))
        request.session['survey_data_temp'] = survey_data
        print(f"Temporary survey data stored in session: {survey_data}")
        return JsonResponse({'success': True, 'message': '설문 데이터가 임시로 저장되었습니다.'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 JSON 데이터 형식입니다.'}, status=400)
    except Exception as e:
        print(f"Error processing survey: {e}")
        return JsonResponse({'success': False, 'error': f'서버 처리 중 오류가 발생했습니다: {str(e)}'}, status=500)


@require_POST
@csrf_protect
def logout_view(request):
    logout(request)
    return redirect('home')  # 로그아웃 후 리디렉션


@login_required
def profile_edit(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            saved_user = user_form.save()
            saved_profile = profile_form.save()
            messages.success(request, '프로필 정보가 성공적으로 업데이트되었습니다!')

            # ✅ 프로필 저장 후, 신체 기록(BodyCompositionRecord) 생성
            # 저장된 프로필에 체중, 골격근량, 체지방량 값이 모두 있을 경우에만 기록합니다.
            if (saved_profile.current_weight and 
                saved_profile.skeletal_muscle_mass and 
                saved_profile.body_fat_mass):
                
                BodyCompositionRecord.objects.create(
                    user=request.user,
                    weight=saved_profile.current_weight,
                    skeletal_muscle_mass=saved_profile.skeletal_muscle_mass,
                    body_fat_mass=saved_profile.body_fat_mass
                )
                messages.info(request, '신체 변화 기록이 추가되었습니다.')

            return redirect('web:services')
        else:
            messages.error(request, '입력된 정보를 다시 확인해주세요.')
    else:
        # ... (GET 요청 부분은 그대로)
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'accounts/profile_edit.html', context)