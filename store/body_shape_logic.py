# store/body_shape_logic.py

try:
    import cv2
    import mediapipe as mp
    import numpy as np
except ImportError:
    pass

# ✅ 함수의 이름이 'advanced' 인지 확인하세요.
def analyze_body_shape_advanced(image_path, output_skeleton_path, output_analysis_path):
    """
    🔥 [최종 업그레이드] 실루엣의 윤곽선(Contour)과 형태(Shape)를 직접 분석하는 함수
    """
    try:
        mp_pose = mp.solutions.pose
        mp_selfie_segmentation = mp.solutions.selfie_segmentation
        mp_drawing = mp.solutions.drawing_utils

        with open(str(image_path), "rb") as f:
            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if image is None: return None, None, "이미지 디코딩 실패"

        image_height, image_width, _ = image.shape
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        with mp_pose.Pose(static_image_mode=True, model_complexity=2) as pose, \
             mp_selfie_segmentation.SelfieSegmentation(model_selection=0) as selfie_segmentation:
            
            pose_results = pose.process(image_rgb)
            segmentation_results = selfie_segmentation.process(image_rgb)

            if not pose_results.pose_landmarks:
                return None, None, "신체 감지 실패"

            binary_mask = (segmentation_results.segmentation_mask > 0.5).astype(np.uint8)
            landmarks = pose_results.pose_landmarks.landmark

            contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours: return None, None, "실루엣 윤곽선 찾기 실패"
            body_contour = max(contours, key=cv2.contourArea)

            shoulder_y = int(((landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y + 
                               landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y) / 2) * image_height)
            hip_y = int(((landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y + 
                          landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y) / 2) * image_height)

            hull = cv2.convexHull(body_contour, returnPoints=False)
            defects = cv2.convexityDefects(body_contour, hull)

            waist_points = []
            if defects is not None:
                for i in range(defects.shape[0]):
                    s, e, f, d = defects[i, 0]
                    far = tuple(body_contour[f][0])
                    if shoulder_y < far[1] < hip_y:
                        waist_points.append({'point': far, 'depth': d / 256.0})

            if not waist_points: return None, None, "허리 지점 측정 실패"
            
            waist_points.sort(key=lambda p: p['point'][0])
            left_waist = min([p for p in waist_points if p['point'][0] < image_width / 2], key=lambda p: p['point'][0], default=None)
            right_waist = max([p for p in waist_points if p['point'][0] > image_width / 2], key=lambda p: p['point'][0], default=None)
            
            if not left_waist or not right_waist:
                deepest_waist = max(waist_points, key=lambda p: p['depth'])
                waist_width = 0
                waist_indentation_depth = deepest_waist['depth']
            else:
                waist_width = right_waist['point'][0] - left_waist['point'][0]
                waist_indentation_depth = (left_waist['depth'] + right_waist['depth']) / 2

            shoulder_width = np.linalg.norm(np.array([landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]) - np.array([landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y])) * image_width
            hip_width = np.linalg.norm(np.array([landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]) - np.array([landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x, landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y])) * image_width
            
            shoulder_to_hip_ratio = shoulder_width / hip_width if hip_width > 0 else 1
            is_curvy_waist = waist_indentation_depth > (image_height * 0.015)
            
            body_shape = 'OVAL'
            if shoulder_to_hip_ratio > 1.05: body_shape = 'INVERTED_TRIANGLE'
            elif shoulder_to_hip_ratio < 0.95: body_shape = 'TRIANGLE'
            else:
                if is_curvy_waist: body_shape = 'HOURGLASS'
                else: body_shape = 'RECTANGLE'
            
            if waist_width > 0 and (waist_width / hip_width) > 0.9: body_shape = 'OVAL'

            analysis_data = {
                'shape_analysis': {
                    'body_shape': body_shape, 'is_curvy_waist': is_curvy_waist,
                    'waist_indentation_depth_ratio': round(waist_indentation_depth / image_height, 4),
                    'shoulder_to_hip_ratio': round(shoulder_to_hip_ratio, 3),
                    'waist_width': int(waist_width), 'shoulder_width': int(shoulder_width), 'hip_width': int(hip_width),
                }
            }

            skeleton_image = image.copy()
            mp_drawing.draw_landmarks(skeleton_image, pose_results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            cv2.imwrite(str(output_skeleton_path), skeleton_image)
            
            analysis_image = image.copy()
            cv2.drawContours(analysis_image, [body_contour], -1, (0, 255, 0), 2)
            hull_points = cv2.convexHull(body_contour)
            cv2.drawContours(analysis_image, [hull_points], -1, (255, 0, 0), 2)
            if left_waist: cv2.circle(analysis_image, left_waist['point'], 10, (0, 0, 255), -1)
            if right_waist: cv2.circle(analysis_image, right_waist['point'], 10, (0, 0, 255), -1)
            cv2.imwrite(str(output_analysis_path), analysis_image)

            return body_shape, analysis_data, "분석 성공"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, None, f"분석 중 오류 발생: {e}"