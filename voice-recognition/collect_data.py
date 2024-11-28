import sounddevice as sd
import soundfile as sf
import os
import time

def collect_training_data():
    sr = 22050  # 采样率
    duration = 1  # 录音时长（秒）
    
    # 创建数据文件夹
    os.makedirs("dataset/snap", exist_ok=True)
    os.makedirs("dataset/non_snap", exist_ok=True)
    
    def record_samples(category, num_samples):
        print(f"\n开始录制{category}样本")
        for i in range(num_samples):
            input(f"按回车开始录制第 {i+1}/{num_samples} 个样本...")
            
            print("录音中...")
            audio = sd.rec(int(duration * sr), samplerate=sr, channels=1)
            sd.wait()
            
            # 保存音频文件
            filename = f"dataset/{category}/{category}_{i}.wav"
            sf.write(filename, audio, sr)
            print(f"已保存到 {filename}")
            time.sleep(0.5)
    
    # 录制打响指声音样本
    record_samples("snap", 20)
    
    # 录制其他环境声音样本
    record_samples("non_snap", 20)

if __name__ == "__main__":
    collect_training_data() 