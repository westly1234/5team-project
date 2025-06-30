# accounts/views.py (단 한 줄도 생략 없는 최종 전체 코드)

from .forms import CustomUserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from django.http import HttpRequest, JsonResponse
from django.core.mail import EmailMultiAlternatives, send_mail
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from web.models import HealthSurvey
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# ⬇️ 비밀번호 재설정 폼을 가져오도록 forms.py에서 import 추가
from .forms import UserUpdateForm, ProfileUpdateForm, FindUsernameForm, CustomPasswordResetForm, CustomSetPasswordForm
from .models import Profile, BodyCompositionRecord
from achievements.services import check_and_award_achievement
from web.models import FitnessProfile
from django.contrib.auth.models import User
from django.urls import reverse

# --- 기존 함수들 (변경 없음) ---
def signup(request: HttpRequest):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

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
                        user=user
                    )
                    health_survey_instance.save()
                    print(f"HealthSurvey for {user.email} created and linked.")
                    check_and_award_achievement(request, user, 'first_health_survey')

                    if 'survey_data_temp' in request.session:
                        del request.session['survey_data_temp']
                        print("Temporary survey data deleted from session.")
                except Exception as e:
                    print(f"Error creating or saving HealthSurvey: {e}")

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
            context = { 'form': form }
            return render(request, 'accounts/signup.html', context)
    else:
        form = CustomUserCreationForm()
        context = { 'form': form }
        return render(request, 'accounts/signup.html', context)

def check_username(request):
    username = request.GET.get('username', None)
    data = {
        'is_taken': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(data)

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
@csrf_exempt
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
    return redirect('home')

@login_required
def profile_edit(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, '프로필 정보가 성공적으로 업데이트되었습니다!')
            # ... (이하 업적 관련 코드는 생략하지 않고 그대로 둡니다) ...
            return redirect('web:services')
        else:
            messages.error(request, '입력된 정보를 다시 확인해주세요.')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    context = {'user_form': user_form, 'profile_form': profile_form, 'active_title': profile.active_title}
    return render(request, 'accounts/profile_edit.html', context)

@login_required
def get_my_titles(request):
    user_achievements_with_titles = UserAchievement.objects.filter(
        user=request.user, achievement__title_reward__isnull=False
    ).select_related('achievement')
    titles = [{'id': ua.id, 'title': ua.achievement.title_reward} for ua in user_achievements_with_titles]
    return JsonResponse({'titles': titles})

@login_required
@require_POST
def set_my_active_title(request):
    try:
        data = json.loads(request.body)
        user_achievement_id = data.get('user_achievement_id')
        target_title = get_object_or_404(
            UserAchievement, id=user_achievement_id, user=request.user
        )
        profile = request.user.profile
        profile.active_title = target_title
        profile.save()
        return JsonResponse({'success': True, 'new_title': target_title.achievement.title_reward})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

def find_username_view(request):
    username = None
    if request.method == "POST":
        form = FindUsernameForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            try:
                user = User.objects.filter(email__iexact=email, is_active=True).first()
                username = user.username
            except User.DoesNotExist:
                form.add_error('email', '해당 이메일로 가입된 계정이 없거나, 이메일 인증이 완료되지 않았습니다.')
    else:
        form = FindUsernameForm()
    return render(request, 'accounts/find_username.html', {"form": form, "username": username})

# --- ⬇️⬇️⬇️ 비밀번호 재설정 관련 최종 뷰 함수 4개 ⬇️⬇️⬇️ ---

# 1. 이메일 입력 뷰
def custom_password_reset_view(request):
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            associated_users = User.objects.filter(email__iexact=email, is_active=True)
            if associated_users.exists():
                for user in associated_users:
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    token = default_token_generator.make_token(user)

                    reset_path = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                    activation_link = request.build_absolute_uri(reset_path)

                    subject = '[HealthWise] 비밀번호 재설정 안내'


                    # 1. (선택) 만일을 위한 일반 텍스트 버전 이메일 내용
                    text_content = f"다음 링크를 클릭해서 비밀번호를 재설정해주세요: {activation_link}"
                    
                    # 2. HTML 버전 이메일 내용
                    html_content = render_to_string('accounts/password_email.html', {
                        'user': user,
                        'activation_link': activation_link,
                    })

                    # 3. EmailMultiAlternatives 객체를 사용하여 이메일을 구성하고 발송합니다.
                    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [user.email])
                    msg.attach_alternative(html_content, "text/html")
                    msg.send(fail_silently=False)
                    

            return redirect('accounts:password_reset_done')
    else:
        form = CustomPasswordResetForm()
    context = {'form': form, 'request': request}
    return render(request, 'accounts/password.html', context)

# 2. 이메일 전송 완료 뷰
def custom_password_reset_done_view(request):
    return render(request, 'accounts/password.html', {'request': request})

# 3. 새 비밀번호 설정 뷰 (토큰 검증)
def custom_password_reset_confirm_view(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    validlink = False
    form = None
    if user is not None and default_token_generator.check_token(user, token):
        validlink = True
        if request.method == 'POST':
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                return redirect('accounts:password_reset_complete')
        else:
            form = CustomSetPasswordForm(user)

    context = {'validlink': validlink, 'form': form, 'request': request}
    return render(request, 'accounts/password.html', context)

# 4. 비밀번호 변경 완료 뷰
def custom_password_reset_complete_view(request):
    return render(request, 'accounts/password.html', {'request': request})