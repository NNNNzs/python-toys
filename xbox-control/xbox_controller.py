#!/usr/bin/env python3
"""
Xbox控制器处理模块
提供Xbox手柄的连接、状态获取和按键事件处理功能
"""

from inputs import get_gamepad
import math
import threading
import time

class XboxController:
    """
    Xbox控制器类
    处理控制器的连接、断开和输入事件
    """
    
    def __init__(self):
        """
        初始化Xbox控制器
        设置初始状态和按键映射
        """
        self.connected = False
        self.running = False
        
        # 初始化所有按键和摇杆的状态
        self.button_states = {
            'BTN_SOUTH': 0,  # A键
            'BTN_EAST': 0,   # B键
            'BTN_WEST': 0,   # X键
            'BTN_NORTH': 0,  # Y键
            'BTN_START': 0,  # 开始键
            'BTN_SELECT': 0, # 选择键
            'BTN_TL': 0,     # 左肩键
            'BTN_TR': 0,     # 右肩键
        }
        
        # 摇杆状态
        self.analog_states = {
            'ABS_X': 0,  # 左摇杆X轴
            'ABS_Y': 0,  # 左摇杆Y轴
            'ABS_RX': 0, # 右摇杆X轴
            'ABS_RY': 0, # 右摇杆Y轴
            'ABS_Z': 0,  # 左扳机
            'ABS_RZ': 0, # 右扳机
        }
        
        # 方向键状态
        self.dpad_states = {
            'ABS_HAT0X': 0, # 方向键X轴
            'ABS_HAT0Y': 0, # 方向键Y轴
        }

    def start(self):
        """
        启动控制器监听
        创建新线程处理输入事件
        """
        self.running = True
        self.connected = True
        self.thread = threading.Thread(target=self._monitor_controller)
        self.thread.daemon = True
        self.thread.start()
        print("Xbox控制器监听已启动")

    def stop(self):
        """
        停止控制器监听
        """
        self.running = False
        self.connected = False
        print("Xbox控制器监听已停止")

    def _monitor_controller(self):
        """
        监控控制器输入的主循环
        持续读取并处理控制器事件
        """
        try:
            while self.running:
                events = get_gamepad()
                for event in events:
                    self._process_event(event)
        except Exception as e:
            print(f"控制器连接错误: {e}")
            self.connected = False
            self.running = False

    def _process_event(self, event):
        """
        处理单个控制器事件
        
        Args:
            event: 控制器事件对象
        """
        if event.ev_type == 'Key':
            if event.code in self.button_states:
                self.button_states[event.code] = event.state
                print(f"按键事件: {event.code} = {event.state}")
                
        elif event.ev_type == 'Absolute':
            if event.code in self.analog_states:
                self.analog_states[event.code] = event.state
                print(f"摇杆/扳机事件: {event.code} = {event.state}")
            elif event.code in self.dpad_states:
                self.dpad_states[event.code] = event.state
                print(f"方向键事件: {event.code} = {event.state}")

    def get_button_state(self, button_code):
        """
        获取指定按键的状态
        
        Args:
            button_code: 按键代码
            
        Returns:
            int: 按键状态（0或1）
        """
        return self.button_states.get(button_code, 0)

    def get_analog_state(self, analog_code):
        """
        获取指定摇杆或扳机的状态
        
        Args:
            analog_code: 摇杆/扳机代码
            
        Returns:
            int: 摇杆/扳机的值
        """
        return self.analog_states.get(analog_code, 0)

    def is_connected(self):
        """
        获取控制器连接状态
        
        Returns:
            bool: 是否已连接
        """
        return self.connected 