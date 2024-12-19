#!/usr/bin/env python3
"""
Xbox控制器可视化界面
使用PyQt6创建图形界面展示控制器状态
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QTimer
from xbox_controller import XboxController

class ControllerWidget(QWidget):
    """控制器状态可视化组件"""
    
    def __init__(self, controller):
        """
        初始化控制器可视化组件
        
        Args:
            controller: XboxController实例
        """
        super().__init__()
        self.controller = controller
        self.setMinimumSize(1000, 800)
        
        # 设置按键颜色
        self.active_color = QColor(0, 255, 0)  # 更改为亮绿色提高区分度
        self.inactive_color = QColor(100, 100, 100)  # 更暗的灰色
        
        # 设置刷新定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(16)  # 约60fps的刷新率
        
    def paintEvent(self, event):
        """
        绘制控制器状态
        
        Args:
            event: 绘制事件
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(240, 240, 240))
        
        # 按照Xbox手柄布局重新排列组件
        # 左摇杆在左上方
        self._draw_stick(painter, 250, 200, 'ABS_X', 'ABS_Y', "左摇杆")
        
        # 右摇杆在右下方
        self._draw_stick(painter, 750, 400, 'ABS_RX', 'ABS_RY', "右摇杆")
        
        # 扳机放在上方
        self._draw_trigger(painter, 150, 50, 'ABS_Z', "LT")
        self._draw_trigger(painter, 850, 50, 'ABS_RZ', "RT")
        
        # 按键放在右上方
        self._draw_buttons(painter, 750, 200)
        
        # 方向键放在左下方
        self._draw_dpad(painter, 250, 400)
        
    def _draw_stick(self, painter, x, y, x_code, y_code, label):
        """
        绘制摇杆
        
        Args:
            painter: QPainter对象
            x: 中心点x坐标
            y: 中心点y坐标
            x_code: X轴状态码
            y_code: Y轴状态码
            label: 摇杆标签
        """
        # 绘制底圆
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.drawEllipse(x-50, y-50, 100, 100)
        
        # 计算摇杆位置（修正Y轴方向）
        stick_x = self.controller.get_analog_state(x_code) / 32768 * 40
        stick_y = -self.controller.get_analog_state(y_code) / 32768 * 40  # 注意这里加了负号
        
        # 绘制摇杆点
        painter.setBrush(self.active_color)
        painter.drawEllipse(int(x + stick_x - 10), int(y + stick_y - 10), 20, 20)
        
        # 绘制标签
        painter.drawText(x-30, y+70, label)
        
    def _draw_trigger(self, painter, x, y, code, label):
        """
        绘制扳机
        
        Args:
            painter: QPainter对象
            x: 左上角x坐标
            y: 左上角y坐标
            code: 扳机状态码
            label: 扳机标签
        """
        # 计算扳机值（0-255）
        value = self.controller.get_analog_state(code)
        height = int((value / 255) * 100)
        
        # 使用渐变色显示扳机状态
        gradient = QColor(0, min(255, height * 2), 0)
        
        # 绘制背景条
        painter.setPen(Qt.GlobalColor.black)
        painter.drawRect(x, y, 30, 100)
        
        # 绘制填充条
        painter.fillRect(x, y + (100 - height), 30, height, gradient)
        
        # 绘制标签
        painter.drawText(x+5, y-10, label)
        
    def _draw_buttons(self, painter, x, y):
        """
        绘制按键状态
        
        Args:
            painter: QPainter对象
            x: 起始x坐标
            y: 起始y坐标
        """
        buttons = {
            'BTN_SOUTH': ('A', x, y+50, QColor(0, 255, 0)),      # A键-绿色
            'BTN_EAST': ('B', x+50, y, QColor(255, 0, 0)),       # B键-红色
            'BTN_WEST': ('X', x-50, y, QColor(0, 0, 255)),       # X键-蓝色
            'BTN_NORTH': ('Y', x, y-50, QColor(255, 255, 0)),    # Y键-黄色
            'BTN_TL': ('LB', x-200, y-150, self.active_color),   # 左肩键
            'BTN_TR': ('RB', x+200, y-150, self.active_color),   # 右肩键
        }
        
        for code, (label, bx, by, active_color) in buttons.items():
            state = self.controller.get_button_state(code)
            if code in ['BTN_TL', 'BTN_TR']:  # 肩键特殊处理
                color = self.active_color if state else self.inactive_color
                # 绘制更大的椭圆形表示肩键
                painter.setBrush(color)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawEllipse(bx-25, by-15, 50, 30)
            else:  # ABXY按键
                color = active_color if state else self.inactive_color
                painter.setBrush(color)
                painter.setPen(Qt.GlobalColor.black)
                painter.drawEllipse(bx-15, by-15, 30, 30)
            
            # 绘制标签（肩键的标签位置调整）
            if code in ['BTN_TL', 'BTN_TR']:
                painter.drawText(bx-10, by+5, label)
            else:
                painter.drawText(bx-5, by+5, label)
            
    def _draw_dpad(self, painter, x, y):
        """
        绘制方向键
        
        Args:
            painter: QPainter对象
            x: 中心x坐标
            y: 中心y坐标
        """
        x_state = self.controller.dpad_states['ABS_HAT0X']
        y_state = self.controller.dpad_states['ABS_HAT0Y']
        
        # 绘制方向键底座
        painter.setPen(Qt.GlobalColor.black)
        painter.drawRect(x-40, y-40, 80, 80)
        
        # 根据状态绘制方向指示
        color = QColor(0, 120, 215)
        if x_state > 0:  # 右
            painter.fillRect(x+10, y-10, 20, 20, color)
        elif x_state < 0:  # 左
            painter.fillRect(x-30, y-10, 20, 20, color)
            
        if y_state > 0:  # 上
            painter.fillRect(x-10, y-30, 20, 20, color)
        elif y_state < 0:  # 下
            painter.fillRect(x-10, y+10, 20, 20, color)

class ControllerWindow(QMainWindow):
    """控制器可视化主窗口"""
    
    def __init__(self, controller):
        """
        初始化主窗口
        
        Args:
            controller: XboxController实例
        """
        super().__init__()
        self.setWindowTitle('Xbox控制器状态可视化')
        self.setStyleSheet("background-color: #f0f0f0;")
        
        # 创建主组件
        self.controller_widget = ControllerWidget(controller)
        self.setCentralWidget(self.controller_widget)
        
        # 设置窗口大小
        self.setMinimumSize(1000, 800)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建控制器实例
    controller = XboxController()
    controller.start()
    
    # 创建并显示窗口
    window = ControllerWindow(controller)
    window.show()
    
    try:
        sys.exit(app.exec())
    finally:
        controller.stop()

if __name__ == '__main__':
    main() 