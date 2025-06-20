from .forms import CustomUserCreationForm
from django.shortcuts import render, redirect, get_object_or_404
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
from .models import Profile, BodyCompositionRecord
from achievements.services import check_and_award_achievement
from web.models import FitnessProfile
from django.http import JsonResponse
from achievements.models import UserAchievement

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
                    check_and_award_achievement(request, user, 'first_health_survey') 

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
            user_form.save()
            saved_profile = profile_form.save(commit=False)
            # ✅ 업적 확인을 위해 이전 값 저장
            old_image = profile.image
            old_target_weight = profile.target_weight
            
            saved_profile.save() # ✅ 여기서 최종 저장
            profile_form.save_m2m() # ManyToMany 필드가 있다면 필요
            messages.success(request, '프로필 정보가 성공적으로 업데이트되었습니다!')

            # ✅ 1. 프로필 관련 업적 확인
            # 프로필 이미지를 처음으로 업로드하거나 변경했을 때
            if saved_profile.image and old_image != saved_profile.image:
                check_and_award_achievement(request, request.user, 'first_profile_image') # '얼굴 도장 쾅!'
            
            # 목표 체중을 처음 설정했을 때
            if saved_profile.target_weight and not old_target_weight:
                check_and_award_achievement(request, request.user, 'first_target_weight') # '목표 설정 완료!'

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
                check_and_award_achievement(request, request.user, 'first_body_record')
                record_count = BodyCompositionRecord.objects.filter(user=request.user).count()
                if record_count >= 10:
                    check_and_award_achievement(request, request.user, 'body_record_10')
                if record_count >= 30:
                    check_and_award_achievement(request, request.user, 'body_record_30')
                messages.info(request, '신체 변화 기록이 추가되었습니다.')

            # ✅ 3. 목표 달성 관련 업적 확인
            # 목표 체중 달성 확인
            if saved_profile.current_weight and saved_profile.target_weight:
                if saved_profile.current_weight <= saved_profile.target_weight:
                    check_and_award_achievement(request, request.user, 'target_weight_achieved')

            # 근육량/체지방량 변화 관련 업적 (BodyCompositionRecord 기록을 바탕으로)
            all_records = BodyCompositionRecord.objects.filter(user=request.user)
            if all_records.count() > 1:
                latest_record = all_records.first() # 최신 기록
                highest_fat = max(r.body_fat_mass for r in all_records)
                highest_muscle = max(r.skeletal_muscle_mass for r in all_records)
                
                # 체지방 감량
                if latest_record.body_fat_mass <= highest_fat - 1:
                    check_and_award_achievement(request, request.user, 'fat_loss_1kg')
                if latest_record.body_fat_mass <= highest_fat - 5:
                    check_and_award_achievement(request, request.user, 'fat_loss_5kg')
                
                # 근육량 증가
                if latest_record.skeletal_muscle_mass >= highest_muscle + 1:
                    check_and_award_achievement(request, request.user, 'muscle_gain_1kg')

            try:
                profile = request.user.profile
                fitness_profile = FitnessProfile.objects.get(user=request.user)

                # 프로필과 피트니스 정보의 모든 필수 필드가 채워졌는지 확인합니다.
                all_fields_filled = all([
                    saved_profile.height, saved_profile.current_weight, saved_profile.target_weight,
                    saved_profile.skeletal_muscle_mass, saved_profile.body_fat_mass,
                    fitness_profile.birth,
                    fitness_profile.gender,
                    fitness_profile.goal,
                    fitness_profile.experience,
                    fitness_profile.frequency,
                    fitness_profile.types
                ])

                if all_fields_filled:
                    check_and_award_achievement(request, request.user, 'profile_perfectionist')

            except FitnessProfile.DoesNotExist:
                # 피트니스 프로필이 없는 사용자는 이 업적을 달성할 수 없습니다.
                pass
            except Exception as e:
                # 이 로직에서 오류가 발생해도 전체 기능이 중단되지 않도록 합니다.
                print(f"프로필 완성도 업적 확인 중 오류 발생: {e}")
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

@login_required
def get_my_titles(request):
    """
    사용자가 보유한 모든 칭호 목록을 JSON으로 반환
    """
    # title_reward가 있는, 즉 칭호를 부여하는 업적만 필터링합니다.
    user_achievements_with_titles = UserAchievement.objects.filter(
        user=request.user, 
        achievement__title_reward__isnull=False
    ).select_related('achievement')

    titles = [{
        'user_achievement_id': ua.id,
        'title': ua.achievement.title_reward,
        'achievement_name': ua.achievement.name,
    } for ua in user_achievements_with_titles]
    
    return JsonResponse({'titles': titles})

@login_required
@require_POST
def set_my_active_title(request):
    """
    사용자의 대표 칭호를 설정
    """
    try:
        data = json.loads(request.body)
        user_achievement_id = data.get('user_achievement_id')

        # 사용자가 실제로 보유한 칭호인지 확인
        target_title = get_object_or_404(
            UserAchievement, 
            id=user_achievement_id, 
            user=request.user,
            achievement__title_reward__isnull=False # 칭호가 있는 업적인지 재확인
        )
        
        profile = request.user.profile
        profile.active_title = target_title
        profile.save()
        
        return JsonResponse({'success': True, 'new_title': target_title.achievement.title_reward})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)