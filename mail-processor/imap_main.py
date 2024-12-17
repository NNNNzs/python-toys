"""
@description IMAP邮件处理程序入口
@author AI Assistant
@date 2024
"""

from imap_client import ImapClient

def main():
    """
    主程序入口
    """
    client = ImapClient()
    
    if client.connect():
        print("成功连接到邮件服务器")
        
        # 获取所有文件夹中的邮件
        client.fetch_all_folders(limit=200)
        
        client.close()
        print("处理完成")
    else:
        print("连接邮件服务器失败")

if __name__ == "__main__":
    main() 