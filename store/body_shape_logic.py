import cv2
import mediapipe as mp
import numpy as np

def analyze_image_for_body_shape(image_path):
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=True, model_complexity=2)

    image = cv2.imread(image_path)
    if image is None:
        return None, "이미지를 읽을 수 없습니다."

    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    if not results.pose_landmarks:
        return None, "사진에서 신체를 감지하지 못했습니다. 더 선명한 전신사진을 사용해주세요."

    landmarks = results.pose_landmarks.landmark

    # 주요 랜드마크 좌표 추출 (어깨, 엉덩이, 허리)
    # MediaPipe의 랜드마크 인덱스를 사용합니다.
    p_shoulder_l = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
    p_shoulder_r = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
    p_hip_l = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
    p_hip_r = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
    # 허리는 엉덩이와 어깨의 중간 지점으로 추정
    p_waist_l = np.array([(p_shoulder_l.x + p_hip_l.x) / 2, (p_shoulder_l.y + p_hip_l.y) / 2])
    p_waist_r = np.array([(p_shoulder_r.x + p_hip_r.x) / 2, (p_shoulder_r.y + p_hip_r.y) / 2])
    
    # 픽셀 너비 계산 (실제 거리가 아닌 비율 계산용)
    shoulder_width = np.linalg.norm(np.array([p_shoulder_l.x, p_shoulder_l.y]) - np.array([p_shoulder_r.x, p_shoulder_r.y]))
    hip_width = np.linalg.norm(np.array([p_hip_l.x, p_hip_l.y]) - np.array([p_hip_r.x, p_hip_r.y]))
    waist_width = np.linalg.norm(p_waist_l - p_waist_r) # 추정치
    
    # 비율 기반 체형 분류 로직
    # 이 수치는 예시이며, 더 정확한 분류를 위해 조정이 필요합니다.
    if shoulder_width * 0.95 <= hip_width <= shoulder_width * 1.05: # 어깨와 엉덩이가 비슷
        if waist_width < hip_width * 0.75:
            body_shape = 'HOURGLASS' # 허리가 잘록하면 모래시계
        else:
            body_shape = 'RECTANGLE' # 허리가 통짜면 직사각형
    elif hip_width > shoulder_width * 1.05:
        body_shape = 'TRIANGLE' # 엉덩이가 넓으면 삼각형
    elif shoulder_width > hip_width * 1.05:
        body_shape = 'INVERTED_TRIANGLE' # 어깨가 넓으면 역삼각형
    else:
        body_shape = 'OVAL' # 기본값 또는 다른 로직 추가

    analysis_data = {
        'shoulder_width': shoulder_width,
        'waist_width': waist_width,
        'hip_width': hip_width,
    }
    
    pose.close()
    return body_shape, analysis_data