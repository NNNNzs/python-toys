import cv2
import numpy as np

# 创建一个简单的火焰图片
def create_fire_image():
    # 创建透明背景
    img = np.zeros((50, 50, 4), dtype=np.uint8)
    
    # 创建火焰形状
    center = (25, 35)
    axes = (10, 20)
    angle = 0
    
    # 绘制火焰主体
    cv2.ellipse(img, center, axes, angle, 0, 360, (0, 165, 255, 255), -1)
    
    # 添加火焰顶部
    pts = np.array([[15, 35], [25, 5], [35, 35]], np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.fillPoly(img, [pts], (0, 255, 255, 255))
    
    # 添加模糊效果
    img = cv2.GaussianBlur(img, (5, 5), 0)
    
    # 保存图片
    cv2.imwrite('fire.png', img)

if __name__ == "__main__":
    create_fire_image() 