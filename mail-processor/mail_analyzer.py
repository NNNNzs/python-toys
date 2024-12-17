#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
邮件分析器：解析.eml文件并使用Gemini进行内容分析
支持多封邮件会话分析和递归处理
"""

import os
import json
import pandas as pd
from email import policy
from email.parser import BytesParser
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from collections import defaultdict
import re
import time
from typing import Dict, List, Optional

# 定义常量
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_MAILS_DIR = os.path.join(BASE_DIR, "downloads", "raw_mails")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# 设置 Clash 代理
PROXY_HOST = '127.0.0.1'
PROXY_PORT = '7888'
PROXY_URL = f'http://{PROXY_HOST}:{PROXY_PORT}'

# 设置环境变量
os.environ['http_proxy'] = PROXY_URL
os.environ['https_proxy'] = PROXY_URL
os.environ['HTTPS_PROXY'] = PROXY_URL
os.environ['HTTP_PROXY'] = PROXY_URL

class MailAnalyzer:
    """
    邮件分析器类，支持会话跟踪和递归处理
    """
    def __init__(self):
        """
        初始化邮��分析器
        """
        print("初始化邮件分析器...")
        load_dotenv()
        
        # 初始化 Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("未找到 GEMINI_API_KEY 环境变量")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        print("Gemini API 初始化成功")
        
        # 初始化数据存储
        self.conversation_threads: Dict[str, List[Dict]] = defaultdict(list)
        self.inventory_data: List[Dict] = []
        
        # 添加统计计数器
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_conversations': 0,
            'analyzed_conversations': 0,
            'failed_analyses': 0
        }
    
    def extract_conversation_id(self, subject: str) -> str:
        """
        从邮件主题中提取会话ID
        
        @param {str} subject - 邮件主题
        @return {str} - 会话ID
        """
        # 移除Re:, Fwd:等前缀
        clean_subject = re.sub(r'^(Re|Fwd|转发|回复|答复):\s*', '', subject, flags=re.IGNORECASE)
        # 移除订单号等特殊字符
        clean_subject = re.sub(r'[#\[\]【】\(\)（）]', '', clean_subject)
        return clean_subject.strip()
    
    def parse_eml(self, eml_path: str) -> Optional[Dict]:
        """
        解析单个.eml文件
        
        @param {str} eml_path - .eml文件路径
        @return {Optional[Dict]} - 解析后的邮件数据，失败返回None
        """
        print(f"\n正在解析邮件: {os.path.basename(eml_path)}")
        try:
            with open(eml_path, 'rb') as fp:
                msg = BytesParser(policy=policy.default).parse(fp)
            
            subject = msg['subject'] or ''
            conversation_id = self.extract_conversation_id(subject)
            print(f"会话ID: {conversation_id}")
            
            # 提取发件人和收件人的邮箱地址
            from_addr = re.findall(r'<(.+?)>', msg['from'])[0] if '<' in msg['from'] else msg['from']
            to_addr = re.findall(r'<(.+?)>', msg['to'])[0] if '<' in msg['to'] else msg['to']
            
            mail_data = {
                'file_path': eml_path,
                'conversation_id': conversation_id,
                'subject': subject,
                'from': from_addr,
                'to': to_addr,
                'date': msg['date'],
                'content': '',
                'timestamp': datetime.strptime(msg['date'].split('(')[0].strip(), 
                                             '%a, %d %b %Y %H:%M:%S %z').timestamp()
            }
            
            content_parts = []
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        content = part.get_content()
                        # 移除多余的空行和空格
                        content = re.sub(r'\n\s*\n', '\n\n', content.strip())
                        content_parts.append(content)
                    except Exception as e:
                        print(f"警告：解析内容部分失败: {str(e)}")
                        try:
                            payload = part.get_payload(decode=True)
                            content = payload.decode('utf-8', errors='ignore')
                            content = re.sub(r'\n\s*\n', '\n\n', content.strip())
                            content_parts.append(content)
                        except Exception as e:
                            print(f"警告：备用解码也失败: {str(e)}")
            
            mail_data['content'] = '\n\n'.join(content_parts)
            print(f"成功解析邮件，内容长度: {len(mail_data['content'])} 字符")
            return mail_data
            
        except Exception as e:
            print(f"错误：解析邮件��败 {eml_path}")
            print(f"错误详情: {str(e)}")
            return None
    
    def extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """
        从 Gemini 响应中提取 JSON 数据
        
        @param {str} response_text - Gemini API 的响应文本
        @return {Optional[Dict]} - 解析后的 JSON 数据，失败返回 None
        """
        try:
            # 1. 直接尝试解析
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                pass
            
            # 2. 尝试从 Markdown 代码块中提取
            json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            matches = re.findall(json_pattern, response_text)
            
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
            
            # 3. 尝试查找第一个 { 到最后一个 } 之间的内容
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1:
                try:
                    return json.loads(response_text[start:end + 1])
                except json.JSONDecodeError:
                    pass
            
            print("无法从响应中提取有效的 JSON 数据")
            print("原始响应:")
            print(response_text)
            return None
            
        except Exception as e:
            print(f"提取 JSON 时发生错误: {str(e)}")
            return None
    
    def analyze_conversation(self, conversation_emails: List[Dict]) -> Optional[Dict]:
        """
        分析整个邮件会话
        
        @param {List[Dict]} conversation_emails - 会话中的所有邮件
        @return {Optional[Dict]} - 分析结果，失败返回None
        """
        conversation_id = conversation_emails[0]['conversation_id']
        print(f"\n开始分析会话: {conversation_id}")
        print(f"会话包含 {len(conversation_emails)} 封邮件")
        
        # 按时间排序邮件
        sorted_emails = sorted(conversation_emails, key=lambda x: x['timestamp'])
        print(f"时间跨度: {sorted_emails[0]['date']} 至 {sorted_emails[-1]['date']}")
        
        # 构建会话上下文
        print("构建会话上下文...")
        conversation_context = "以下是一组相关邮件的往来记录，请分析最终确认的商品和库存信息：\n\n"
        for idx, email in enumerate(sorted_emails, 1):
            conversation_context += f"""
            === 邮件 {idx} ===
            时间：{email['date']}
            发件人：{email['from']}
            收件人：{email['to']}
            主题：{email['subject']}
            内容：
            {email['content']}
            
            """
        
        prompt = f"""
        请仔细分析以上邮件往来记录，提取最终确认的商品和库存信息。
        
        要求：
        1. 只提取最终确认的信息，忽略中间讨论的临时数据
        2. 如果有多个商品，请分别列出
        3. 如果没有明确提到的信息，对应字段返回null
        4. 价格统一使用美元单位
        
        请以JSON格式返回，包含以下字段：
        1. product_name: 商品名称
        2. quantity: 确认的数量
        3. unit_price: 最终单价(USD)
        4. total_price: 总价(USD)
        5. delivery_date: 确认的交货日期
        6. special_requirements: 特殊要求或备注
        7. status: 订单状态(confirmed/pending/cancelled)
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"正在调用 Gemini API 进行分析... (尝试 {attempt + 1}/{max_retries})")
                response = self.model.generate_content(prompt + conversation_context)
                
                # 从响应中提取 JSON
                analysis_result = self.extract_json_from_response(response.text)
                if analysis_result:
                    print("分析完成，成功解析JSON响应")
                    
                    result = {
                        'conversation_id': conversation_id,
                        'first_mail_date': sorted_emails[0]['date'],
                        'last_mail_date': sorted_emails[-1]['date'],
                        'mail_count': len(sorted_emails),
                        'analysis_result': analysis_result
                    }
                    
                    return result
                else:
                    print(f"警告：无法提取有效的JSON (尝试 {attempt + 1}/{max_retries})")
                    if attempt == max_retries - 1:
                        raise json.JSONDecodeError("无法从响应中提取有效的JSON", response.text, 0)
                    time.sleep(1)
                    continue
                    
            except Exception as e:
                print(f"分析失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    self.stats['failed_analyses'] += 1
                    return None
                time.sleep(1)
    
    def process_all_emails(self):
        """
        处理所有邮件并按会话分组
        """
        print(f"\n开始扫描目录: {RAW_MAILS_DIR}")
        
        # 统计总文件数
        for root, _, files in os.walk(RAW_MAILS_DIR):
            self.stats['total_files'] += sum(1 for f in files if f.endswith('.eml'))
        
        print(f"找到 {self.stats['total_files']} 个.eml文件")
        
        # 处理所有文件
        for root, _, files in os.walk(RAW_MAILS_DIR):
            for file in files:
                if file.endswith('.eml'):
                    eml_path = os.path.join(root, file)
                    try:
                        mail_data = self.parse_eml(eml_path)
                        if mail_data:
                            self.conversation_threads[mail_data['conversation_id']].append(mail_data)
                            self.stats['processed_files'] += 1
                        else:
                            self.stats['failed_files'] += 1
                        print(f"进度: {self.stats['processed_files']}/{self.stats['total_files']}")
                    except Exception as e:
                        self.stats['failed_files'] += 1
                        print(f"处理失败 {eml_path}: {e}")
        
        self.stats['total_conversations'] = len(self.conversation_threads)
        print(f"\n文件处理完成. 共发现 {self.stats['total_conversations']} 个会话")
        
        # 分析会话
        print("\n开始分析会话...")
        for conversation_id, emails in self.conversation_threads.items():
            analysis_result = self.analyze_conversation(emails)
            if analysis_result:
                self.inventory_data.append(analysis_result)
                self.stats['analyzed_conversations'] += 1
        
        # 打印统计信息
        print("\n处理统计:")
        print(f"总文件数: {self.stats['total_files']}")
        print(f"成功处理: {self.stats['processed_files']}")
        print(f"处理失败: {self.stats['failed_files']}")
        print(f"总会话数: {self.stats['total_conversations']}")
        print(f"成功分析: {self.stats['analyzed_conversations']}")
        print(f"分析失败: {self.stats['failed_analyses']}")
    
    def generate_excel_report(self):
        """
        生成Excel报告
        """
        print("\n开始生成报告...")
        
        if not self.inventory_data:
            print("警告：没有可用的分析数据")
            return
        
        # 确保报告目录存在
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        # 生成报告文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(REPORTS_DIR, f"inventory_report_{timestamp}.xlsx")
        
        # 转换数据为DataFrame
        print("正在处理数据...")
        
        # 展平嵌套的JSON数据
        flattened_data = []
        for item in self.inventory_data:
            flat_item = {
                'conversation_id': item['conversation_id'],
                'first_mail_date': item['first_mail_date'],
                'last_mail_date': item['last_mail_date'],
                'mail_count': item['mail_count']
            }
            # 添加分析结果
            if isinstance(item['analysis_result'], dict):
                for key, value in item['analysis_result'].items():
                    flat_item[key] = value
            flattened_data.append(flat_item)
        
        df = pd.DataFrame(flattened_data)
        
        # 保存到Excel
        print(f"保存Excel报告: {output_path}")
        df.to_excel(output_path, index=False)
        
        # 生成JSON备份
        json_path = output_path.replace('.xlsx', '.json')
        print(f"保存JSON备份: {json_path}")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.inventory_data, f, ensure_ascii=False, indent=2)
        
        print("\n报告生成完成!")
        print(f"Excel报告: {output_path}")
        print(f"JSON备份: {json_path}")

def main():
    """
    主函数
    """
    print("=" * 50)
    print("邮件分析器启动")
    print("=" * 50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"源目录: {RAW_MAILS_DIR}")
    print(f"报告目录: {REPORTS_DIR}")
    print("=" * 50)
    
    try:
        # 创建分析器实例
        analyzer = MailAnalyzer()
        
        # 处理所有邮件
        analyzer.process_all_emails()
        
        # 生成报告
        analyzer.generate_excel_report()
        
        print("\n处理完成!")
        
    except Exception as e:
        print(f"\n错误：程序执行失败")
        print(f"错误详情: {str(e)}")
        raise

if __name__ == "__main__":
    main() 