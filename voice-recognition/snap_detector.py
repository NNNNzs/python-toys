import librosa
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import sounddevice as sd
import os
import soundfile as sf

class SnapDetector:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100)
        self.sr = 22050  # 采样率
        self.duration = 1  # 录音时长（秒）
        
    def extract_features(self, audio_path):
        # 加载音频文件
        y, sr = librosa.load(audio_path, sr=self.sr)
        
        # 提取特征
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        
        # 计算均值作为特征
        features = np.concatenate([
            mfcc.mean(axis=1),
            spectral_centroids.mean(axis=1),
            spectral_rolloff.mean(axis=1)
        ])
        
        return features
    
    def train(self, data_folder):
        features = []
        labels = []
        
        # 遍历数据文件夹中的音频文件
        for label in ['snap', 'non_snap']:
            folder = os.path.join(data_folder, label)
            for file in os.listdir(folder):
                if file.endswith('.wav'):
                    audio_path = os.path.join(folder, file)
                    feature = self.extract_features(audio_path)
                    features.append(feature)
                    labels.append(1 if label == 'snap' else 0)
        
        # 训练模型
        X_train, X_test, y_train, y_test = train_test_split(
            np.array(features), np.array(labels), test_size=0.2
        )
        self.model.fit(X_train, y_train)
        
        # 输出准确率
        score = self.model.score(X_test, y_test)
        print(f"模型准确率: {score:.2f}")
    
    def record_audio(self):
        print("开始录音...")
        audio = sd.rec(int(self.duration * self.sr), 
                      samplerate=self.sr, 
                      channels=1)
        sd.wait()
        return audio.flatten()
    
    def predict_live(self):
        while True:
            # 录制音频
            audio = self.record_audio()
            
            # 保存临时文件
            temp_file = "temp_recording.wav"
            sf.write(temp_file, audio, self.sr)
            
            # 提取特征并预测
            features = self.extract_features(temp_file)
            prediction = self.model.predict([features])[0]
            
            if prediction == 1:
                print("检测到打响指声音！")
            else:
                print("未检测到打响指声音")
            
            # 删除临时文件
            os.remove(temp_file) 