import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import os
from pathlib import Path

# 添加系统通知相关的导入
import subprocess

# 初始化MediaPipe，降低置信度阈值以提高性能
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,  # 修改为检测两只手
    min_detection_confidence=0.5,  # 降低检测置信度
    min_tracking_confidence=0.5    # 降低跟踪置信度
)
mp_draw = mp.solutions.drawing_utils

# 初始化摄像头
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("无法打开摄像头，请检查权限设置")
    exit()

# 设置摄像头分辨率为较低的值以提高性能
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 获取屏幕尺寸
screen_width, screen_height = pyautogui.size()
# 设置鼠标移动的平滑度
pyautogui.FAILSAFE = False
pyautogui.MINIMUM_DURATION = 0

# 定义前一帧的手指位置和时间
prev_x, prev_y = 0, 0
prev_time = 0
# 添加移动平滑因子
smoothing_factor = 0.5
# 添加移动速度系数
speed_factor = 1.5

# 添加打响指状态追踪变量
last_snap_time = 0
snap_cooldown = 3.0  # 修改打响指冷却时间为3秒

# 添加拍掌状态追踪变量
last_clap_time = 0
clap_cooldown = 1.0
last_hand_positions = []  # 用于存储前几帧的手掌位置
position_history_size = 3  # 存储的历史帧数

# 修改状态追踪变量
prev_positions = {'left': {'x': 0, 'y': 0}, 'right': {'x': 0, 'y': 0}}
hand_states = {'left': None, 'right': None}  # 用于追踪每只手的状态

# 加载火焰图片
current_dir = Path(__file__).parent
fire_img = cv2.imread(str(current_dir / 'fire.png'), cv2.IMREAD_UNCHANGED)
if fire_img is None:
    raise Exception("无法加载火焰图片")
# 调整火焰大小
fire_img = cv2.resize(fire_img, (50, 50))

# 修改火焰效果的控制变量
fire_effects = {
    'left': {'active': False, 'start_time': 0, 'finger_id': None},  # finger_id 表示哪个手指有火焰
    'right': {'active': False, 'start_time': 0, 'finger_id': None}
}
fire_duration = 3.0  # 火焰持续时间（秒）

# 添加手指接触检测的阈值
finger_touch_threshold = 0.03

def overlay_transparent(background, overlay, x, y):
    """在背景图片上叠加透明图片"""
    if x < 0 or y < 0:
        return background
    
    h, w = overlay.shape[:2]
    
    # 确保坐标不超出背景图片范围
    if y + h > background.shape[0] or x + w > background.shape[1]:
        return background
    
    if overlay.shape[2] < 4:
        overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2BGRA)
    
    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0
    
    background_section = background[y:y + h, x:x + w]
    background[y:y + h, x:x + w] = background_section * (1 - mask) + overlay_image * mask
    
    return background

def count_fingers(hand_landmarks):
    """计算伸出的手指数量"""
    # 指尖的索引
    tips = [8, 12, 16, 20]  # 食指、中指、无名指、小指的指尖索引
    thumb_tip = 4  # 拇指指尖索引
    
    fingers = []
    
    # 检查拇指
    thumb_tip_x = hand_landmarks.landmark[thumb_tip].x
    thumb_base_x = hand_landmarks.landmark[2].x
    
    # 根据拇指尖与拇指根部的x坐标判断拇指是否伸出
    fingers.append(thumb_tip_x < thumb_base_x)
    
    # 检查其他手指
    for tip in tips:
        tip_y = hand_landmarks.landmark[tip].y
        pip_y = hand_landmarks.landmark[tip - 2].y  # 第二关节的y坐标
        
        # 如果指尖的y坐标小于第二关节的y坐标，则认为手指伸出
        fingers.append(tip_y < pip_y)
    
    return sum(fingers)  # 返回伸出的手指数量

def calculate_distance(point1, point2):
    """计算两点之间的距离"""
    return np.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def is_fist(hand_landmarks):
    """判断是否为握拳状态"""
    # 获取所有指尖和掌心的关键点
    thumb_tip = np.array([hand_landmarks.landmark[4].x, hand_landmarks.landmark[4].y])
    index_tip = np.array([hand_landmarks.landmark[8].x, hand_landmarks.landmark[8].y])
    middle_tip = np.array([hand_landmarks.landmark[12].x, hand_landmarks.landmark[12].y])
    ring_tip = np.array([hand_landmarks.landmark[16].x, hand_landmarks.landmark[16].y])
    pinky_tip = np.array([hand_landmarks.landmark[20].x, hand_landmarks.landmark[20].y])
    
    wrist = np.array([hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y])
    
    # 计算所有指尖到手腕的距离
    distances = [
        calculate_distance(thumb_tip, wrist),
        calculate_distance(index_tip, wrist),
        calculate_distance(middle_tip, wrist),
        calculate_distance(ring_tip, wrist),
        calculate_distance(pinky_tip, wrist)
    ]
    
    return all(d < 0.25 for d in distances)  # 调整阈值使检测更灵敏

def send_notification(message):
    """发送 Mac 系统通知"""
    apple_script = f'display notification "{message}" with title "手势检测"'
    subprocess.run(['osascript', '-e', apple_script])

def is_snapping(hand_landmarks):
    """检测打响指手势"""
    # 获取拇指尖和中指尖的坐标
    thumb_tip = np.array([hand_landmarks.landmark[4].x, hand_landmarks.landmark[4].y])
    middle_tip = np.array([hand_landmarks.landmark[12].x, hand_landmarks.landmark[12].y])
    
    # 计算拇指和中指之间的距离
    distance = calculate_distance(thumb_tip, middle_tip)
    
    # 如果距离小于阈值，认为是打响指手势
    return distance < 0.05  # 可以调整这个阈值

def get_palm_direction(hand_landmarks):
    """获取手掌朝向"""
    # 使用手掌中心点和中指根部的点来判断手掌朝向
    palm_center = np.array([hand_landmarks.landmark[9].x, hand_landmarks.landmark[9].y, hand_landmarks.landmark[9].z])
    middle_finger_base = np.array([hand_landmarks.landmark[0].x, hand_landmarks.landmark[0].y, hand_landmarks.landmark[0].z])
    
    # 计算z轴方向的差值，判断手掌是否朝向对方
    return palm_center[2] - middle_finger_base[2]

def calculate_hand_velocity(current_positions):
    """计算手掌移动速度"""
    if len(last_hand_positions) < 2:
        return 0
    
    # 计算最近两帧的速度
    prev = last_hand_positions[-1]
    curr = current_positions
    
    velocity = np.sqrt(
        (curr[0][0] - prev[0][0])**2 + 
        (curr[0][1] - prev[0][1])**2 +
        (curr[1][0] - prev[1][0])**2 + 
        (curr[1][1] - prev[1][1])**2
    )
    return velocity

def is_clapping(hand_landmarks_list):
    """检测双手拍掌手势（优化版）"""
    if len(hand_landmarks_list) != 2:
        return False
    
    # 获取两只手的关键点
    hand1, hand2 = hand_landmarks_list[0], hand_landmarks_list[1]
    
    # 检查手掌朝向
    direction1 = get_palm_direction(hand1)
    direction2 = get_palm_direction(hand2)
    
    # 如果手掌没有相对朝向，不是拍掌
    if direction1 * direction2 >= 0:
        return False
    
    # 获取多个检测点的坐标
    hand1_points = {
        'palm': np.array([hand1.landmark[9].x, hand1.landmark[9].y]),
        'index': np.array([hand1.landmark[5].x, hand1.landmark[5].y]),
        'pinky': np.array([hand1.landmark[17].x, hand1.landmark[17].y])
    }
    
    hand2_points = {
        'palm': np.array([hand2.landmark[9].x, hand2.landmark[9].y]),
        'index': np.array([hand2.landmark[5].x, hand2.landmark[5].y]),
        'pinky': np.array([hand2.landmark[17].x, hand2.landmark[17].y])
    }
    
    # 计算多个点之间的距离
    distances = {
        'palm': calculate_distance(hand1_points['palm'], hand2_points['palm']),
        'index': calculate_distance(hand1_points['index'], hand2_points['index']),
        'pinky': calculate_distance(hand1_points['pinky'], hand2_points['pinky'])
    }
    
    # 更新手掌位置历史
    current_positions = [(hand1_points['palm'][0], hand1_points['palm'][1]),
                        (hand2_points['palm'][0], hand2_points['palm'][1])]
    
    # 计算手掌移动速度
    velocity = calculate_hand_velocity(current_positions)
    
    # 更新位置历史
    last_hand_positions.append(current_positions)
    if len(last_hand_positions) > position_history_size:
        last_hand_positions.pop(0)
    
    # 综合多个条件判断是否为拍掌
    is_close = all(d < 0.2 for d in distances.values())  # 所有检测点都够近
    is_moving = velocity > 0.1  # 手掌在快速移动
    
    return is_close and is_moving

def get_hand_side(hand_landmarks, results):
    """判断是左手还是右手"""
    # 通过手腕和大拇指的相对位置判断
    wrist = hand_landmarks.landmark[0]
    thumb = hand_landmarks.landmark[4]
    
    # 在翻转的图像中，如果大拇指在手腕的左边，就是右手
    return 'right' if thumb.x < wrist.x else 'left'

def get_finger_tips(hand_landmarks):
    """获取所有手指尖的坐标"""
    finger_tips = {
        'thumb': np.array([hand_landmarks.landmark[4].x, hand_landmarks.landmark[4].y]),  # 拇指
        'index': np.array([hand_landmarks.landmark[8].x, hand_landmarks.landmark[8].y]),  # 食指
        'middle': np.array([hand_landmarks.landmark[12].x, hand_landmarks.landmark[12].y]),  # 中指
        'ring': np.array([hand_landmarks.landmark[16].x, hand_landmarks.landmark[16].y]),  # 无名指
        'pinky': np.array([hand_landmarks.landmark[20].x, hand_landmarks.landmark[20].y])  # 小指
    }
    return finger_tips

def check_finger_touch(hand1_landmarks, hand2_landmarks):
    """检测两只手的手指接触"""
    hand1_tips = get_finger_tips(hand1_landmarks)
    hand2_tips = get_finger_tips(hand2_landmarks)
    
    # 检查每个手指之间的接触
    for finger1_name, finger1_pos in hand1_tips.items():
        for finger2_name, finger2_pos in hand2_tips.items():
            distance = calculate_distance(finger1_pos, finger2_pos)
            if distance < finger_touch_threshold:
                return (finger1_name, finger2_name)
    
    return None

def get_finger_id(finger_name):
    """将手指名称转换为对应的手指ID"""
    finger_map = {
        'thumb': 4,
        'index': 8,
        'middle': 12,
        'ring': 16,
        'pinky': 20
    }
    return finger_map[finger_name]

def process_fire_transfer(hand1_landmarks, hand2_landmarks, hand1_side, hand2_side, current_time):
    """处理火焰传递"""
    # 检查手指接触
    touch_result = check_finger_touch(hand1_landmarks, hand2_landmarks)
    
    if touch_result:
        finger1_name, finger2_name = touch_result
        # 检查是否有一个手指有火焰
        if (fire_effects[hand1_side]['active'] and not fire_effects[hand2_side]['active']):
            # 从手1传递到手2
            fire_effects[hand2_side]['active'] = True
            fire_effects[hand2_side]['start_time'] = current_time
            fire_effects[hand2_side]['finger_id'] = get_finger_id(finger2_name)
            return True
        elif (fire_effects[hand2_side]['active'] and not fire_effects[hand1_side]['active']):
            # 从手2传递到手1
            fire_effects[hand1_side]['active'] = True
            fire_effects[hand1_side]['start_time'] = current_time
            fire_effects[hand1_side]['finger_id'] = get_finger_id(finger1_name)
            return True
    return False

def process_hand(hand_landmarks, img, hand_side, current_time):
    """处理单个手的所有手势"""
    global prev_positions, last_snap_time, fire_effects
    
    # 获取食指指尖的坐标
    index_finger = hand_landmarks.landmark[8]
    x = int(index_finger.x * screen_width)
    y = int(index_finger.y * screen_height)
    
    # 转换为图像坐标系
    img_x = int(index_finger.x * img.shape[1])
    img_y = int(index_finger.y * img.shape[0])
    
    # 判断手势状态
    is_fist_state = is_fist(hand_landmarks)
    hand_states[hand_side] = 'fist' if is_fist_state else 'open'
    
    # 检查并更新火焰效果状态
    if fire_effects[hand_side]['active']:
        if current_time - fire_effects[hand_side]['start_time'] > fire_duration:
            fire_effects[hand_side]['active'] = False
            fire_effects[hand_side]['finger_id'] = None
        else:
            # 获取当前激活的手指尖坐标
            finger_id = fire_effects[hand_side]['finger_id'] or 8  # 默认使用食指
            finger_tip = hand_landmarks.landmark[finger_id]
            img_x = int(finger_tip.x * img.shape[1])
            img_y = int(finger_tip.y * img.shape[0])
            # 在手指上显示火焰
            fire_x = img_x - fire_img.shape[1] // 2
            fire_y = img_y - fire_img.shape[0]
            img = overlay_transparent(img, fire_img, fire_x, fire_y)
    
    # 在图像上显示手的状态
    status_y = 30 if hand_side == 'right' else 60
    cv2.putText(img, f"{hand_side.title()}: {'Moving' if is_fist_state else 'Waiting'}", 
                (10, status_y), cv2.FONT_HERSHEY_SIMPLEX, 1, 
                (0, 255, 0) if is_fist_state else (0, 0, 255), 2)
    
    if is_fist_state:
        # 只有当有前一帧位置时才移动鼠标
        if prev_positions[hand_side]['x'] != 0:
            dx = (x - prev_positions[hand_side]['x']) * speed_factor
            dy = (y - prev_positions[hand_side]['y']) * speed_factor
            current_x, current_y = pyautogui.position()
            
            # 应用平滑因子
            new_x = current_x + int(dx * smoothing_factor)
            new_y = current_y + int(dy * smoothing_factor)
            
            # 确保鼠标位置在屏幕范围内
            new_x = max(0, min(new_x, screen_width))
            new_y = max(0, min(new_y, screen_height))
            
            pyautogui.moveTo(new_x, new_y)
    else:
        # 检测打响指
        if is_snapping(hand_landmarks) and (current_time - last_snap_time) > snap_cooldown:
            send_notification(f"检测到{hand_side}手打响指")
            last_snap_time = current_time
            # 激活火焰效果（默认在食指上）
            fire_effects[hand_side]['active'] = True
            fire_effects[hand_side]['start_time'] = current_time
            fire_effects[hand_side]['finger_id'] = 8  # 食指ID
            
            cv2.putText(img, f"Snap ({hand_side})!", (10, 150 if hand_side == 'right' else 180), 
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    
    # 更新前一帧位置
    prev_positions[hand_side]['x'] = x
    prev_positions[hand_side]['y'] = y
    
    return x, y

try:
    while True:
        # 计算帧率
        current_time = time.time()
        fps = 1 / (current_time - prev_time) if prev_time else 0
        prev_time = current_time
        
        success, img = cap.read()
        if not success:
            continue
            
        # 缩小图像以提高处理速度
        img = cv2.resize(img, (640, 480))
        img = cv2.flip(img, 1)
        
        # 转换颜色空间并处理
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)
        
        # 重置手状态
        hand_states = {'left': None, 'right': None}
        
        # 如果检测到手
        if results.multi_hand_landmarks:
            # 如果检测到两只手，处理火焰传递
            if len(results.multi_hand_landmarks) == 2:
                hand1_landmarks = results.multi_hand_landmarks[0]
                hand2_landmarks = results.multi_hand_landmarks[1]
                hand1_side = get_hand_side(hand1_landmarks, results)
                hand2_side = get_hand_side(hand2_landmarks, results)
                
                # 检测并处理火焰传递
                if process_fire_transfer(hand1_landmarks, hand2_landmarks, 
                                      hand1_side, hand2_side, current_time):
                    cv2.putText(img, "Fire Transferred!", (10, 240), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
            
            # 处理每只手的手势
            for hand_landmarks in results.multi_hand_landmarks:
                # 绘制手部关键点
                mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # 判断是左手还是右手
                hand_side = get_hand_side(hand_landmarks, results)
                
                # 处理这只手的所有手势
                x, y = process_hand(hand_landmarks, img, hand_side, current_time)
                
                # 显示坐标信息
                cv2.putText(img, f"{hand_side.title()}: ({x}, {y})", 
                          (10, 90 if hand_side == 'right' else 120), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        
        # 显示帧率
        cv2.putText(img, f"FPS: {int(fps)}", (10, 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        # 显示图像
        cv2.imshow("Hand Mouse Control", img)
        
        # 按'q'退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows() 