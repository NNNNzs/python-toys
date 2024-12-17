from PIL import Image
import os
import platform

def create_icon():
    """从logo_N.png创建图标"""
    try:
        # 读取logo图片
        icon_path = os.path.join(os.path.dirname(__file__), 'logo_N.png')
        if not os.path.exists(icon_path):
            raise FileNotFoundError(f"找不到图标文件：{icon_path}")
            
        img = Image.open(icon_path)
        img = img.convert('RGBA')
        
        # 确保图片是正方形
        size = min(img.size)
        left = (img.size[0] - size) // 2
        top = (img.size[1] - size) // 2
        img = img.crop((left, top, left + size, top + size))
        
        # 调整到标准尺寸
        img = img.resize((512, 512), Image.Resampling.LANCZOS)
        
        if platform.system().lower() == 'darwin':
            # macOS版本
            sizes = [(16,16), (32,32), (64,64), (128,128), (256,256), (512,512)]
            os.makedirs('icon.iconset', exist_ok=True)
            
            for size in sizes:
                resized = img.resize(size, Image.Resampling.LANCZOS)
                resized.save(f'icon.iconset/icon_{size[0]}x{size[0]}.png')
            
            os.system('iconutil -c icns icon.iconset')
            os.system('rm -rf icon.iconset')
            print("已生成 icon.icns")
            
        else:
            # Windows版本
            sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
            icons = []
            for size in sizes:
                icons.append(img.resize(size, Image.Resampling.LANCZOS))
            
            icons[0].save('icon.ico', format='ICO', sizes=sizes, append_images=icons[1:])
            print("已生成 icon.ico")
        
        return True
        
    except Exception as e:
        print(f"创建图标时出错: {str(e)}")
        return False

if __name__ == '__main__':
    create_icon() 