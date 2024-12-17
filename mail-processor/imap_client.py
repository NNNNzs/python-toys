"""
@description 邮件客户端核心实现 - IMAP版本
@author AI Assistant
@date 2024
"""

import imaplib
import email
import os
import re
from datetime import datetime
from email.header import decode_header
from config import EMAIL_CONFIG

# 添加IMAP UTF-7解码支持
def decode_imap_utf7(text):
    """
    解码IMAP UTF-7编码的文件夹名
    
    @param text: IMAP UTF-7编码的文本
    @return: 解码后的文本
    """
    if '&' not in text:
        return text
        
    try:
        # 导入imapclient库中的utf7解码函数
        from imapclient.imap_utf7 import decode as decode_utf7
        return decode_utf7(text)
    except ImportError:
        print("请安装imapclient: pip3 install imapclient")
        return text

class ImapClient:
    """
    IMAP邮件客户端类
    """
    
    def __init__(self):
        """
        初始化邮件客户端
        """
        self.server = None
        self.base_path = EMAIL_CONFIG['save_path']
        
        # 创建基础下载目录
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            
        # 创建邮件原件存储目录
        self.raw_mail_path = os.path.join(self.base_path, 'raw_mails')
        if not os.path.exists(self.raw_mail_path):
            os.makedirs(self.raw_mail_path)
        
        # 如果已存在的目录是编码格式，尝试重命名为解码后的格式
        self.fix_encoded_folders()

    def fix_encoded_folders(self):
        """
        修复已存在的编码格式文件夹名
        """
        if not os.path.exists(self.raw_mail_path):
            return
        
        try:
            # 遍历raw_mails目录
            for folder_name in os.listdir(self.raw_mail_path):
                if '&' in folder_name:
                    old_path = os.path.join(self.raw_mail_path, folder_name)
                    if os.path.isdir(old_path):
                        # 解码文件夹名
                        decoded_name = decode_imap_utf7(folder_name)
                        new_path = os.path.join(self.raw_mail_path, decoded_name)
                        
                        # 如果解码后的目录不存在，则重命名
                        if not os.path.exists(new_path):
                            print(f"重命名文件夹: {folder_name} -> {decoded_name}")
                            os.rename(old_path, new_path)
        except Exception as e:
            print(f"修复文件夹名称时出错: {str(e)}")

    def connect(self):
        """
        连接到IMAP邮件服务器
        """
        try:
            print(f"正在连接到服务器: {EMAIL_CONFIG['imap_server']}...")
            self.server = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'])
            print(f"正在登录号: {EMAIL_CONFIG['email']}...")
            self.server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
            print("登录成功!")
            return True
        except Exception as e:
            print(f"连接失败: {str(e)}")
            return False

    def list_folders(self):
        """
        列出服务器上的所有文件夹
        @return: 文件夹列表
        """
        print("\n开始获取邮箱文件夹列表...")
        folders = []
        try:
            _, folder_list = self.server.list()
            print(f"服务器返回 {len(folder_list)} 个文件夹")
            
            for folder_info in folder_list:
                try:
                    folder_info_str = folder_info.decode('utf-8', errors='replace')
                    print(f"原始文件夹信息: {folder_info_str}")
                    
                    # 提取文件夹名称
                    if 'INBOX' in folder_info_str:
                        if folder_info_str.endswith('INBOX'):
                            folder_name = 'INBOX'
                        else:
                            # 处理 INBOX 子文件夹
                            folder_name = folder_info_str.split('INBOX.')[-1].strip('"')
                            # 解码IMAP UTF-7编码
                            folder_name = decode_imap_utf7(folder_name)
                    else:
                        # 处理其他文件夹
                        parts = folder_info_str.split('"')
                        folder_name = next((p for p in parts if p and not p.startswith('.') and p != '"'), None)
                        if folder_name:
                            folder_name = decode_imap_utf7(folder_name)
                    
                    if folder_name:
                        folders.append(folder_name)
                        print(f"找到有效文件夹: {folder_name}")
                    else:
                        print("跳过空文件夹名")
                    
                except Exception as e:
                    print(f"解析文件夹名失败: {str(e)}")
                    print(f"问题文件夹信息: {folder_info_str}")
                    continue
                
            print(f"共找到 {len(folders)} 个有效文件夹")
            return folders
            
        except Exception as e:
            print(f"获取文件夹列表失败: {str(e)}")
            return []

    def sanitize_filename(self, filename):
        """
        清理文件名，移除非法字符
        
        @param filename: 原始文件名
        @return: 清理后的文件名
        """
        # 移除非法字符
        filename = re.sub(r'[\\/*?:"<>|]', '', filename)
        # 将空格替换为下划线
        filename = filename.replace(' ', '_')
        return filename

    def get_mail_folder(self, imap_folder, subject, date):
        """
        获取邮件对应的本地存储文件夹
        
        @param imap_folder: IMAP服务器上的文件夹名
        @param subject: 邮件主题
        @param date: 邮件日期
        @return: 文件夹路径
        """
        # 解码IMAP文件夹名
        imap_folder = decode_imap_utf7(imap_folder)
        
        # 清理文件夹名和主题作为文件夹名
        folder_name = self.sanitize_filename(subject)
        date_prefix = date.strftime("%Y%m%d")
        folder_name = f"{date_prefix}_{folder_name}"
        
        # 创建IMAP文件夹对应的本地目录
        imap_folder_path = os.path.join(self.base_path, self.sanitize_filename(imap_folder))
        if not os.path.exists(imap_folder_path):
            os.makedirs(imap_folder_path)
        
        # 创建完整路径
        folder_path = os.path.join(imap_folder_path, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        return folder_path

    def save_raw_mail(self, email_content, imap_folder, subject, date):
        """
        保存邮件原件
        
        @param email_content: 邮件原始内容
        @param imap_folder: IMAP文件夹名
        @param subject: 邮件主题
        @param date: 邮件日期
        """
        # 解码IMAP文件夹名
        imap_folder = decode_imap_utf7(imap_folder)
        
        # 创建IMAP文件夹对应的原件目录
        folder_path = os.path.join(self.raw_mail_path, self.sanitize_filename(imap_folder))
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            
        # 生成文件名
        date_str = date.strftime("%Y%m%d_%H%M%S")
        filename = f"{date_str}_{self.sanitize_filename(subject)}.eml"
        filepath = os.path.join(folder_path, filename)
        
        # 保存原邮件
        with open(filepath, 'wb') as f:
            f.write(email_content)
        print(f"已保存邮件原件: {imap_folder}/{filename}")

    def get_email_date(self, email_message):
        """
        获取邮件日期
        
        @param email_message: 邮件消息对象
        @return: datetime对象
        """
        date_str = email_message.get('Date')
        try:
            date = email.utils.parsedate_to_datetime(date_str)
        except:
            date = datetime.now()
        return date

    def get_attachments(self, email_message, folder_path):
        """
        获取邮件中的附件
        
        @param email_message: 邮件消息对象
        @param folder_path: 附件保存路径
        """
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            try:
                filename = part.get_filename()
                if filename:
                    # 解码文件名
                    filename = self.decode_header_safe(filename)
                    
                    # 清理文件名
                    filename = self.sanitize_filename(filename)
                    
                    # 保存附件
                    filepath = os.path.join(folder_path, filename)
                    with open(filepath, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    print(f"已保存附件: {filename}")
            except Exception as e:
                print(f"处理附件失败: {str(e)}")
                continue

    def process_email(self, email_id, folder_name):
        """
        处理单邮件
        
        @param email_id: 邮件ID
        @param folder_name: IMAP文件夹名
        """
        try:
            print(f"正在获取邮件内容... (ID: {email_id})")
            _, msg_data = self.server.fetch(email_id, '(RFC822)')
            email_body = msg_data[0][1]
            print("邮件内容获取成功，正在解析...")
            
            email_message = email.message_from_bytes(email_body)
            
            # 获取邮件主题
            subject = self.decode_header_safe(email_message["Subject"])
            print(f"邮件主题: {subject}")
            
            # 获取邮件日期
            date = self.get_email_date(email_message)
            print(f"邮件日期: {date}")
            
            # 保存邮件原件
            print("正在保存邮件原件...")
            self.save_raw_mail(email_body, folder_name, subject, date)
            
            # 根据配置决定是否下载附件
            if EMAIL_CONFIG.get('download_attachments', False):
                # 获取该邮件的专属文件夹
                folder_path = self.get_mail_folder(folder_name, subject, date)
                print(f"邮件保存路径: {folder_path}")
                
                # 保存附件
                print("正在处理附件...")
                self.get_attachments(email_message, folder_path)
            else:
                print("已跳过附件下载（根据配置）")
            
        except Exception as e:
            print(f"处理邮件失败: {str(e)}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")

    def fetch_emails(self, folder_name="INBOX", limit=10):
        """
        获取指定文件夹中的邮件及其附件
        """
        try:
            print(f"\n开始处理文件夹: {folder_name}")
            
            # 选择文件夹（处理INBOX特殊情况）
            if folder_name != "INBOX" and not folder_name.startswith('"'):
                folder_name = f'INBOX.{folder_name}'
            folder_name = f'"{folder_name}"' if ' ' in folder_name else folder_name
            
            print(f"正在选择文件夹: {folder_name}")
            status, data = self.server.select(folder_name)
            
            if status != 'OK':
                # 如果选择失败，尝试不带引号
                folder_name = folder_name.strip('"')
                print(f"重试选择文件夹: {folder_name}")
                status, data = self.server.select(folder_name)
                
                if status != 'OK':
                    print(f"选择文件夹失败: {folder_name}, 状态: {status}, 信息: {data}")
                    return
            
            print("文件夹选择成功，正在获取邮件列表...")
            
            # 获取邮件ID列表
            _, messages = self.server.search(None, 'ALL')
            email_ids = messages[0].split()
            total_emails = len(email_ids)
            
            if not email_ids:
                print(f"文件夹 {folder_name} 中没有邮件")
                return
            
            print(f"文件��中共有 {total_emails} 封邮件")
            process_count = min(limit, total_emails)
            print(f"将处理最新的 {process_count} 封邮件")
            
            # 处理最新的N封邮件
            for i, email_id in enumerate(email_ids[-limit:], 1):
                print(f"\n正在处理第 {i}/{process_count} 封邮件 (ID: {email_id})")
                self.process_email(email_id, folder_name)
                
        except Exception as e:
            print(f"获取邮件失败: {str(e)}")
            print(f"错误类型: {type(e)}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")

    def fetch_all_folders(self, limit=10):
        """
        获取所有文件夹中的邮件
        
        @param limit: 每个文件夹获取的邮件数量限制
        """
        print("\n开始获取所有文件夹的邮件...")
        folders = self.list_folders()
        print(f"\n共找到 {len(folders)} 个文件夹，开始处理...")
        
        for i, folder in enumerate(folders, 1):
            print(f"\n处理第 {i}/{len(folders)} 个文件夹: {folder}")
            self.fetch_emails(folder, limit)

    def close(self):
        """
        关闭连接
        """
        if self.server:
            self.server.logout() 

    def decode_header_safe(self, header):
        """
        安全解码邮件头信息
        
        @param header: 邮件头信息
        @return: 解码后的文本
        """
        if header is None:
            return "无主题"
        
        try:
            # 解码邮件头
            decoded_header = decode_header(header)
            
            # 处理解码结果
            result = []
            for text, charset in decoded_header:
                if isinstance(text, bytes):
                    try:
                        # 尝试使用指定的字符集
                        if charset:
                            text = text.decode(charset)
                        else:
                            # 尝试常用编码
                            for encoding in ['utf-8', 'gb18030', 'gb2312', 'big5']:
                                try:
                                    text = text.decode(encoding)
                                    break
                                except UnicodeDecodeError:
                                    continue
                    except Exception:
                        # 如果所有尝试都失败，使用原始字节
                        text = text.decode('utf-8', errors='replace')
                result.append(str(text))
            
            return " ".join(result)
        except Exception as e:
            print(f"解码邮件头失败: {str(e)}")
            return "解码失败的主题"
  