from snap_detector import SnapDetector

def main():
    detector = SnapDetector()
    
    # 训练模型
    print("正在训练模型...")
    detector.train("dataset")
    
    # 实时检测
    print("\n开始实时检测，按Ctrl+C停止...")
    try:
        detector.predict_live()
    except KeyboardInterrupt:
        print("\n检测已停止")

if __name__ == "__main__":
    main() 