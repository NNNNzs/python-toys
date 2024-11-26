import cv2
import dlib
import numpy as np
from math import hypot, atan2, degrees

class GazeTrackingSystem:
    def __init__(self):
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        self.cap = cv2.VideoCapture(0)
        
        # 获取屏幕尺寸
        self.screen_width = 1920
        self.screen_height = 1080
        
        # 3D模型点
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # 鼻尖
            (0.0, -330.0, -65.0),        # 下巴
            (-225.0, 170.0, -135.0),     # 左眼左角
            (225.0, 170.0, -135.0),      # 右眼右角
            (-150.0, -150.0, -125.0),    # 左嘴角
            (150.0, -150.0, -125.0)      # 右嘴角
        ])
        
        # 相机参数（需要校准）
        self.focal_length = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.camera_center = (self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)/2,
                            self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)/2)
        self.camera_matrix = np.array([
            [self.focal_length, 0, self.camera_center[0]],
            [0, self.focal_length, self.camera_center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        # 畸变系数
        self.dist_coeffs = np.zeros((4,1))
        
        # 校准参数
        self.calibrated = False
        self.calibration_points = []
        self.head_pos_neutral = None

    def get_head_pose(self, shape):
        """获取头部姿态"""
        # 获取关键点
        image_points = np.array([
            (shape.part(30).x, shape.part(30).y),     # 鼻尖
            (shape.part(8).x, shape.part(8).y),       # 下巴
            (shape.part(36).x, shape.part(36).y),     # 左眼左角
            (shape.part(45).x, shape.part(45).y),     # 右眼右角
            (shape.part(48).x, shape.part(48).y),     # 左嘴角
            (shape.part(54).x, shape.part(54).y)      # 右嘴角
        ], dtype=np.float64)

        # 解算头部姿态
        success, rotation_vec, translation_vec = cv2.solvePnP(
            self.model_points, image_points, self.camera_matrix, self.dist_coeffs)

        if success:
            # 转换旋转向量为欧拉角
            rotation_mat, _ = cv2.Rodrigues(rotation_vec)
            pose_mat = cv2.hconcat((rotation_mat, translation_vec))
            _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)
            return euler_angles
        return None

    def get_gaze_direction(self, eye_points, facial_landmarks, frame):
        """计算眼球位置和视线方向"""
        eye_region = np.array([(facial_landmarks.part(point).x, facial_landmarks.part(point).y) for point in eye_points])
        
        # 创建眼睛区域的掩码
        height, width = frame.shape[:2]
        mask = np.zeros((height, width), np.uint8)
        cv2.fillPoly(mask, [eye_region], 255)
        
        # 提取眼睛区域
        eye = cv2.bitwise_and(frame, frame, mask=mask)
        gray_eye = cv2.cvtColor(eye, cv2.COLOR_BGR2GRAY)
        
        # 使用自适应阈值找到眼球
        thresh = cv2.adaptiveThreshold(gray_eye, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY_INV, 11, 2)
        
        # 计算眼球中心
        moments = cv2.moments(thresh)
        if moments["m00"] != 0:
            eye_cx = int(moments["m10"] / moments["m00"])
            eye_cy = int(moments["m01"] / moments["m00"])
            return (eye_cx, eye_cy)
        return None

    def calibrate(self):
        """校准过程"""
        print("请保持头部正对屏幕中心，按空格键确认")
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray)
            
            if len(faces) == 1:
                landmarks = self.predictor(gray, faces[0])
                head_pose = self.get_head_pose(landmarks)
                
                if head_pose is not None:
                    # 将numpy数组转换为普通数字
                    pitch = float(head_pose[0])
                    yaw = float(head_pose[1])
                    roll = float(head_pose[2])
                    
                    cv2.putText(frame, f"Head Pose: {pitch:.2f}, {yaw:.2f}, {roll:.2f}",
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
            cv2.imshow("Calibration", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                self.head_pos_neutral = head_pose
                self.calibrated = True
                break
            elif key == ord('q'):
                break

    def calculate_screen_position(self, gaze_left, gaze_right, head_pose):
        """根据眼球位置和头部姿态计算屏幕注视点"""
        if not self.calibrated or head_pose is None:
            return None
        
        # 计算头部偏移
        pitch_diff = head_pose[0] - self.head_pos_neutral[0]
        yaw_diff = head_pose[1] - self.head_pos_neutral[1]
        
        # 结合眼球位置和头部姿态
        if gaze_left and gaze_right:
            gaze_x = (gaze_left[0] + gaze_right[0]) / 2
            gaze_y = (gaze_left[1] + gaze_right[1]) / 2
            
            # 考虑头部转动的影响
            screen_x = int(self.screen_width * (0.5 + yaw_diff/30.0 + (gaze_x - self.camera_center[0])/self.focal_length))
            screen_y = int(self.screen_height * (0.5 + pitch_diff/30.0 + (gaze_y - self.camera_center[1])/self.focal_length))
            
            return (screen_x, screen_y)
        return None

    def run(self):
        # 首先进行校准
        self.calibrate()
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray)
            
            for face in faces:
                landmarks = self.predictor(gray, face)
                head_pose = self.get_head_pose(landmarks)
                
                # 获取左右眼的视线方向
                left_eye = [36, 37, 38, 39, 40, 41]
                right_eye = [42, 43, 44, 45, 46, 47]
                
                gaze_left = self.get_gaze_direction(left_eye, landmarks, frame)
                gaze_right = self.get_gaze_direction(right_eye, landmarks, frame)
                
                # 计算屏幕上的注视点
                screen_pos = self.calculate_screen_position(gaze_left, gaze_right, head_pose)
                
                if screen_pos:
                    # 在frame上显示注视点
                    cv2.circle(frame, (screen_pos[0]//4, screen_pos[1]//4), 5, (0, 255, 0), -1)
                    cv2.putText(frame, f"视线位置: ({screen_pos[0]}, {screen_pos[1]})", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # 显示头部姿态信息
                if head_pose is not None:
                    cv2.putText(frame, f"头部角度: ({int(head_pose[0])}, {int(head_pose[1])}, {int(head_pose[2])})", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            cv2.imshow("眼球追踪", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    system = GazeTrackingSystem()
    system.run() 