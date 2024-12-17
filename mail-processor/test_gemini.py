#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gemini API 测试脚本
用于测试 Gemini API 的连接和基本功能
"""

import os
import json
import time
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import retry

# 设置 Clash 代理
PROXY_HOST = '127.0.0.1'
PROXY_PORT = '7888'
PROXY_URL = f'http://{PROXY_HOST}:{PROXY_PORT}'

# 设置环境变量
os.environ['http_proxy'] = PROXY_URL
os.environ['https_proxy'] = PROXY_URL
os.environ['HTTPS_PROXY'] = PROXY_URL
os.environ['HTTP_PROXY'] = PROXY_URL

# requests 代理设置
PROXIES = {
    'http': PROXY_URL,
    'https': PROXY_URL
}

def check_ip():
    """
    检查当前IP地址和位置
    """
    print("\n检查当前IP信息...")
    try:
        response = requests.get('https://ipapi.co/json/', proxies=PROXIES, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"当前IP: {data.get('ip')}")
            print(f"国家/地区: {data.get('country_name')} ({data.get('country_code')})")
            print(f"城市: {data.get('city')}")
            return data.get('country_code') not in ['CN']  # 确保不是中国大陆IP
    except Exception as e:
        print(f"检查IP失败: {str(e)}")
    return False

def test_api_key():
    """
    测试 API 密钥是否存在和格式是否正确
    """
    print("\n1. 测试 API 密钥...")
    
    # 加载环境变量
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("错误: 未找到 GEMINI_API_KEY 环境变量")
        print("请确保在 .env 文件中设置了 GEMINI_API_KEY")
        return False
    
    if not api_key.startswith('AI'):
        print("警告: API 密钥格式可能不正确，应该以'AI'开头")
        return False
    
    print("API 密钥格式正确 ✓")
    return True

def test_network_connection():
    """
    测试与 Google API 的网络连接
    """
    print("\n2. 测试网络连接...")
    
    # 首先测试代理是否工作
    try:
        print("测试代理连接...")
        response = requests.get('https://www.google.com', 
                              proxies=PROXIES, 
                              timeout=5,
                              verify=True)
        print(f"Google 连接测试成功: {response.status_code}")
    except Exception as e:
        print(f"代理测试失败: {str(e)}")
        print("请检查 Clash 是否正确配置，并确保选择了支持的地区节点（如美国、日本等）")
        return False
    
    try:
        response = requests.get(
            'https://generativelanguage.googleapis.com/v1beta/models',
            proxies=PROXIES,
            timeout=5,
            verify=True
        )
        print(f"API 端点响应状态码: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"API 连接失败: {str(e)}")
        print(f"当前代理设置: {PROXY_URL}")
        return False

def test_gemini_connection():
    """
    测试 Gemini API 连接
    """
    print("\n3. 测试 Gemini API 连接...")
    
    if not check_ip():
        print("警告: 当前IP可能不在支持的地区，请切换代理节点到支持的地区（如美国、日本等）")
        return False
    
    try:
        # 配置 API
        api_key = os.getenv('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        print("API 配置成功")
        
        # 设置超时时间
        timeout = 10
        start_time = time.time()
        
        print("正在获取模型列表...")
        while time.time() - start_time < timeout:
            try:
                models = genai.list_models()
                print("\n可用模型列表:")
                for model in models:
                    print(f"- {model.name}")
                return True
            except Exception as e:
                print(f"尝试失败，正在重试... ({str(e)})")
                if "User location is not supported" in str(e):
                    print("错误: 当前IP地区不被支持，请切换到支持的地区节点")
                    return False
                time.sleep(1)
        
        print(f"获取模型列表超时 ({timeout}秒)")
        return False
        
    except Exception as e:
        print(f"连接测试失败: {str(e)}")
        return False

@retry.Retry(predicate=retry.if_exception_type(Exception))
def test_simple_generation():
    """
    测试简单的内容生成
    """
    print("\n4. 测试简单内容生成...")
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hello, what's 1+1?")
        print("\n测试响应:")
        print(response.text)
        return True
    except Exception as e:
        print(f"生成测试失败: {str(e)}")
        return False

def test_gemini_generation():
    """
    测试 Gemini 内容生成功能
    """
    print("\n5. 测试 JSON 内容生成...")
    
    try:
        # 创建模型实例
        model = genai.GenerativeModel('gemini-pro')
        
        # 测试简单问题
        prompt = "请用JSON格式返回以下信息：商品名称='测试商品'，数量=100，单价=99.9"
        
        print("\n发送测试请求...")
        print(f"提示词: {prompt}")
        
        # 生成响应
        response = model.generate_content(prompt)
        
        print("\n接收到响应:")
        print(response.text)
        
        # 尝试解析JSON
        try:
            json_response = json.loads(response.text)
            print("\nJSON解析成功:")
            print(json.dumps(json_response, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print("\n警告: 响应不是有效的JSON格式")
        
        return True
    except Exception as e:
        print(f"生成测试失败: {str(e)}")
        return False

def main():
    """
    主函数
    """
    print("=" * 50)
    print("Gemini API 测试工具")
    print("=" * 50)
    
    # 逐步测试
    if not test_api_key():
        print("\nAPI 密钥测试失败 ✗")
        return
    
    if not test_network_connection():
        print("\n网络连接测试失败 ✗")
        return
    
    if not test_gemini_connection():
        print("\nGemini API 连接测试失败 ✗")
        return
    
    if not test_simple_generation():
        print("\n简单生成测试失败 ✗")
        return
    
    if not test_gemini_generation():
        print("\nJSON 生成测试失败 ✗")
        return
    
    print("\n所有测试完成! ✓")

if __name__ == "__main__":
    main() 