import cv2
import face_recognition
import numpy as np
import os
import json
from datetime import datetime

class FaceRecognitionSystem:
    def __init__(self):
        # 存储已知人脸的编码和对应的名字
        self.known_face_encodings = []
        self.known_face_names = []
        self.face_data_file = "face_data.json"
        
        # 加载已存储的人脸数据
        self.load_face_data()
        
        # 初始化摄像头
        self.video_capture = cv2.VideoCapture(0)

    def load_face_data(self):
        if os.path.exists(self.face_data_file):
            with open(self.face_data_file, 'r') as f:
                data = json.load(f)
                self.known_face_encodings = [np.array(enc) for enc in data['encodings']]
                self.known_face_names = data['names']

    def save_face_data(self):
        data = {
            'encodings': [enc.tolist() for enc in self.known_face_encodings],
            'names': self.known_face_names
        }
        with open(self.face_data_file, 'w') as f:
            json.dump(data, f)

    def add_new_face(self, frame, encoding):
        name = input("检测到新面孔！请输入此人姓名: ")
        self.known_face_encodings.append(encoding)
        self.known_face_names.append(name)
        self.save_face_data()
        return name

    def run(self):
        while True:
            ret, frame = self.video_capture.read()
            if not ret:
                break

            # 将BGR格式转换为RGB格式
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 缩小图像以加快处理速度
            small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.25, fy=0.25)
            
            # 检测人脸位置
            face_locations = face_recognition.face_locations(small_frame)
            face_encodings = face_recognition.face_encodings(small_frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                name = "未知"

                if True in matches:
                    first_match_index = matches.index(True)
                    name = self.known_face_names[first_match_index]
                elif len(face_locations) == 1:
                    name = self.add_new_face(frame, face_encoding)

                # 将坐标转换回原始图像大小
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                # 在图像上绘制方框
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
                
                # 确保name是UTF-8编码的字符串
                if isinstance(name, str):
                    name = name.encode('utf-8').decode('utf-8')
                
                # 直接使用cv2.putText显示文字
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)

            # 窗口标题也使用UTF-8编码
            cv2.imshow('人脸识别系统'.encode('utf-8').decode('utf-8'), frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.video_capture.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    system = FaceRecognitionSystem()
    system.run() 