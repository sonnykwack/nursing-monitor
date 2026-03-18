import mediapipe as mp
import time
from alert import send_alert

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
pose    = mp_pose.Pose()

# 설정값
FALL_SPEED_THRESHOLD = 0.2
FALL_CONFIRM_TIME    = 3.0
STANDING_THRESHOLD   = 0.6

# 상태 변수
prev_hip_y        = None
prev_time         = None
fall_suspect_time = None
was_standing      = False
fall_alert_sent   = False

def detect(frame):
    global prev_hip_y, prev_time, fall_suspect_time
    global was_standing, fall_alert_sent

    import cv2
    rgb          = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result       = pose.process(rgb)
    current_time = time.time()

    status = "정상"
    color  = (0, 255, 0)

    if result.pose_landmarks:
        landmarks = result.pose_landmarks.landmark
        left_hip  = landmarks[mp_pose.PoseLandmark.LEFT_HIP].y
        right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP].y
        hip_y     = (left_hip + right_hip) / 2

        import cv2
        cv2.putText(frame, f"hip_y: {hip_y:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        if prev_hip_y is not None and prev_time is not None:
            time_diff  = current_time - prev_time
            hip_change = hip_y - prev_hip_y
            speed      = hip_change / time_diff if time_diff > 0 else 0

            if speed > FALL_SPEED_THRESHOLD and was_standing and not fall_alert_sent:
                if fall_suspect_time is None:
                    fall_suspect_time = current_time
                    print("⚠️  낙상 의심! 지켜보는 중...")
                elif current_time - fall_suspect_time >= FALL_CONFIRM_TIME:
                    print("🚨 낙상 확정! 알림 전송 중...")
                    send_alert("낙상 감지 — 즉시 확인 바랍니다", "101호")
                    fall_alert_sent = True
            else:
                if hip_y < STANDING_THRESHOLD:
                    fall_suspect_time = None
                    fall_alert_sent   = False

            if fall_alert_sent:
                status = "낙상 경보!"
                color  = (0, 0, 255)
            elif fall_suspect_time:
                status = "낙상 의심"
                color  = (0, 165, 255)

        was_standing = hip_y < STANDING_THRESHOLD
        prev_hip_y   = hip_y
        prev_time    = current_time

        mp_draw.draw_landmarks(frame, result.pose_landmarks,
                               mp_pose.POSE_CONNECTIONS)

    cv2.putText(frame, status, (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    return frame