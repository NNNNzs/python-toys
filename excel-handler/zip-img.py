from openpyxl import load_workbook
from openpyxl.drawing.image import Image
from PIL import Image as PILImage
import io
import os
import sys
from datetime import datetime
import wx
import platform

class CompressionMode:
    """压缩模式"""
    QUALITY = "质量优先"  # 保持较高质量，文件可能较大
    SIZE = "体积优先"     # 优先确保文件小于目标大小
    BALANCED = "平衡模式"  # 在质量和大小之间取平衡

class ExcelImageCompressor:
    """
    Excel图片压缩工具
    用于压缩Excel文件中的图片并生成新的Excel文件
    """
    def __init__(self, log_callback=None):
        # 检测操作系统
        self.is_windows = platform.system().lower() == 'windows'
        # 默认压缩设置
        self.compression_settings = {
            CompressionMode.QUALITY: {"min_quality": 60, "max_size_kb": 500},
            CompressionMode.SIZE: {"min_quality": 5, "max_size_kb": 200},
            CompressionMode.BALANCED: {"min_quality": 30, "max_size_kb": 300}
        }
        self.log_callback = log_callback
        
    def log(self, message):
        """输出日志"""
        print(message)  # 保持控制台输出
        if self.log_callback:
            wx.CallAfter(self.log_callback, message)  # 线程安全的GUI更新
        
    def normalize_path(self, path):
        """标准化文件路径，处理不同操作系统的路径差异"""
        return os.path.normpath(path)

    def calculate_new_size(self, width, height, max_size_kb):
        """计算保持宽高比的新尺寸"""
        # 估算目标像素数（基于经验值）
        target_pixels = max_size_kb * 1024 * 0.5  # 0.5是经验系数
        current_pixels = width * height
        
        if current_pixels <= target_pixels:
            return width, height
            
        scale = (target_pixels / current_pixels) ** 0.5
        return int(width * scale), int(height * scale)

    def compress_image(self, image_data, max_size_kb=200, compression_mode=CompressionMode.BALANCED):
        """
        压缩图片数据
        
        Args:
            image_data: 原始图片数据
            max_size_kb: 目标文件大小（KB）
            compression_mode: 压缩模式
        
        Returns:
            bytes: 压缩后的图片数据
        """
        try:
            settings = self.compression_settings[compression_mode]
            min_quality = settings["min_quality"]
            max_size_kb = settings["max_size_kb"]

            # 打开图片
            if isinstance(image_data, io.BytesIO):
                image_data = image_data.getvalue()
            img = PILImage.open(io.BytesIO(image_data))
            
            # 保存原始尺寸
            original_width, original_height = img.size
            
            # 如果图片模式是RGBA，转换为RGB
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                elif img.mode == 'LA':
                    background.paste(img, mask=img.split()[1])
                elif img.mode == 'P':
                    background.paste(img, mask=img.convert('RGBA').split()[3])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 初始质量
            quality = 95
            output = io.BytesIO()
            
            # 首先尝试仅调整质量
            while quality >= min_quality:
                output.seek(0)
                output.truncate()
                img.save(output, format='JPEG', quality=quality)
                if len(output.getvalue()) <= max_size_kb * 1024:
                    break
                quality -= 5
            
            # 如果仅调整质量不够，则需要调整尺寸
            if quality < min_quality:
                new_width, new_height = self.calculate_new_size(
                    original_width, original_height, max_size_kb
                )
                img = img.resize((new_width, new_height), PILImage.LANCZOS)
                quality = min(95, quality + 20)  # 提高一些质量
                
                output.seek(0)
                output.truncate()
                img.save(output, format='JPEG', quality=quality)
            
            return output.getvalue()
        except Exception as e:
            raise Exception(f"压缩图片时出错: {str(e)}")

    def process_excel(self, file_path, compression_mode=CompressionMode.BALANCED):
        """处理Excel文件"""
        try:
            file_path = self.normalize_path(file_path)
            self.log(f"正在处理文件：{file_path}")
            
            wb = load_workbook(file_path)
            processed_images = 0
            total_images = 0
            
            for sheet in wb.worksheets:
                images = sheet._images.copy()
                total_images += len(images)
                
                if not images:
                    continue
                
                sheet._images.clear()
                
                for i, img in enumerate(images, 1):
                    self.log(f"正在压缩第 {i}/{len(images)} 张图片...")
                    try:
                        if hasattr(img, '_data'):
                            image_data = img._data()
                        else:
                            image_data = img.ref
                        
                        compressed_data = self.compress_image(
                            image_data, 
                            compression_mode=compression_mode
                        )
                        
                        new_img = Image(io.BytesIO(compressed_data))
                        new_img.anchor = img.anchor
                        new_img.width = img.width
                        new_img.height = img.height
                        
                        sheet._images.append(new_img)
                        processed_images += 1
                    except Exception as e:
                        self.log(f"处理第 {i} 张图片时出错：{str(e)}")
                        sheet._images.append(img)

            file_dir = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            name, ext = os.path.splitext(file_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_file_path = os.path.join(file_dir, f"{name}_compressed_{timestamp}{ext}")
            new_file_path = self.normalize_path(new_file_path)

            wb.save(new_file_path)
            
            message = (f"处理完成！\n"
                      f"压缩模式：{compression_mode}\n"
                      f"共处理 {processed_images}/{total_images} 张图片\n"
                      f"新文件保存在：\n{new_file_path}")
            self.log(message)
            wx.MessageBox(message, "成功", wx.OK | wx.ICON_INFORMATION)
            return True
            
        except Exception as e:
            error_message = f"处理文件时出错：\n{str(e)}"
            self.log(error_message)
            wx.MessageBox(error_message, "错误", wx.OK | wx.ICON_ERROR)
            return False

class MainFrame(wx.Frame):
    def __init__(self):
        size = (650, 500) if platform.system().lower() == 'windows' else (600, 500)
        super().__init__(parent=None, title='Excel图片压缩工具', size=size)
        self.init_ui()
        self.Center()
        
    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # 文件选择部分
        label = wx.StaticText(panel, label="选择要处理的Excel文件：")
        vbox.Add(label, 0, wx.ALL | wx.EXPAND, 5)
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.file_path = wx.TextCtrl(panel)
        browse_btn = wx.Button(panel, label="浏览...")
        hbox.Add(self.file_path, 1, wx.EXPAND | wx.RIGHT, 5)
        hbox.Add(browse_btn, 0)
        vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, 5)
        
        # 压缩模式选择
        mode_label = wx.StaticText(panel, label="选择压缩模式：")
        vbox.Add(mode_label, 0, wx.ALL | wx.EXPAND, 5)
        
        self.mode_choice = wx.Choice(panel, choices=[
            CompressionMode.QUALITY,
            CompressionMode.BALANCED,
            CompressionMode.SIZE
        ])
        self.mode_choice.SetSelection(1)  # 默认选择平衡模式
        vbox.Add(self.mode_choice, 0, wx.ALL | wx.EXPAND, 5)
        
        # 处理按钮
        process_btn = wx.Button(panel, label="开始处理")
        vbox.Add(process_btn, 0, wx.ALL | wx.EXPAND, 5)
        
        # 添加日志文本框
        log_label = wx.StaticText(panel, label="处理日志：")
        vbox.Add(log_label, 0, wx.ALL | wx.EXPAND, 5)
        
        self.log_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        vbox.Add(self.log_text, 1, wx.ALL | wx.EXPAND, 5)
        
        panel.SetSizer(vbox)
        
        # 绑定事件
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        process_btn.Bind(wx.EVT_BUTTON, self.on_process)
        
    def log(self, message):
        """添加日志到文本框"""
        self.log_text.AppendText(f"{message}\n")
        
    def on_browse(self, event):
        with wx.FileDialog(self, "选择Excel文件", wildcard="Excel文件 (*.xlsx;*.xls)|*.xlsx;*.xls",
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.file_path.SetValue(fileDialog.GetPath())
            
    def on_process(self, event):
        file_path = self.file_path.GetValue()
        if not file_path:
            wx.MessageBox("请先选择Excel文件！", "错误", wx.OK | wx.ICON_ERROR)
            return
        
        # 清空日志
        self.log_text.SetValue("")
        
        compression_mode = self.mode_choice.GetString(self.mode_choice.GetSelection())
        compressor = ExcelImageCompressor(log_callback=self.log)
        compressor.process_excel(file_path, compression_mode)

if __name__ == '__main__':
    try:
        app = wx.App()
        frame = MainFrame()
        frame.Show()
        app.MainLoop()
    except Exception as e:
        # 写入错误日志
        with open('error_log.txt', 'w', encoding='utf-8') as f:
            f.write(f"程序启动错误：{str(e)}")
        # 显示错误消息
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("错误", f"程序启动失败：{str(e)}\n详细信息已写入error_log.txt")
