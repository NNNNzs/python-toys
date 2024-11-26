import cv2
import mediapipe as mp
import time

# 初始化手部识别模块
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=2)

# 显示手势数字的映射
gesture_mapping = {
    0: '0',
    1: '1',
    2: '2',
    3: '3',
    4: '4',
    5: '5',
    6: '6',
    7: '7',
    8: '8',
    9: '9'
}

def recognize_gestures(hand_landmarks):
    # 获取手指的关键点坐标
    finger_tips = [
        hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP],
        hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    ]

    # 计算伸展的手指数量
    extended_fingers = 0
    for tip in finger_tips:
        if tip.y < hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].y:  # 判断手指是否伸展
            extended_fingers += 1

    # 返回识别到的数字（0-5）
    return [extended_fingers]  # 这里返回的数字是伸展的手指数量

# 打开摄像头
cap = cv2.VideoCapture(0)

# FPS计时器
prev_time = time.time()

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # 镜像翻转
    frame = cv2.flip(frame, 1)

    # 转换颜色空间
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    # 计算FPS
    current_time = time.time()
    fps = 1 / (current_time - prev_time)
    prev_time = current_time

    if results.multi_hand_landmarks:
        left_hand_number = None
        right_hand_number = None

        for hand_landmarks in results.multi_hand_landmarks:
            # 识别手势
            number = recognize_gestures(hand_landmarks)
            if hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].x < frame.shape[1] / 2:
                left_hand_number = number
            else:
                right_hand_number = number

            # 绘制手部关键点
            mp.solutions.drawing_utils.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        # 显示结果
        if left_hand_number is not None and right_hand_number is not None:
            left_gesture = gesture_mapping[left_hand_number[0]]
            right_gesture = gesture_mapping[right_hand_number[0]]
            print(f"左手: {left_gesture}, 右手: {right_gesture}")
            cv2.putText(frame, f"显示: {left_gesture}{right_gesture}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    # 显示FPS
    cv2.putText(frame, f'FPS: {int(fps)}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # 显示视频流
    cv2.imshow('Hand Gesture Recognition', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
