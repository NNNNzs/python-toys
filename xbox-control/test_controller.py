#!/usr/bin/env python3
"""
Xbox控制器测试模块
"""

from xbox_controller import XboxController
import time

def main():
    """
    主函数，测试Xbox控制器功能
    """
    # 创建控制器实例
    controller = XboxController()
    
    try:
        # 启动控制器监听
        controller.start()
        
        print("控制器测试启动...")
        print("按Ctrl+C退出")
        
        # 保持程序运行，直到用户中断
        while True:
            if not controller.is_connected():
                print("控制器已断开连接")
                break
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n程序已终止")
    finally:
        controller.stop()

if __name__ == "__main__":
    main() 