#!/usr/bin/env python3
"""
电信优选IP自动更新程序
从指定API获取Cloudflare优选IP，过滤电信线路并保存到GitHub仓库
"""

import requests
from bs4 import BeautifulSoup
import os
import json
from datetime import datetime
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ip_updater.log')
    ]
)

logger = logging.getLogger(__name__)

class TelecomIPUpdater:
    def __init__(self):
        self.target_url = "https://api.uouin.com/cloudflare.html"
        self.output_file = "telecom_ips.txt"
        self.telecom_keywords = ['电信', 'China Telecom', 'CT', 'telecom']
        
    def fetch_ips_data(self):
        """从API获取IP数据"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            logger.info(f"开始从 {self.target_url} 获取数据")
            response = requests.get(self.target_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 检查编码
            if response.encoding.lower() == 'iso-8859-1':
                response.encoding = response.apparent_encoding
                
            logger.info("数据获取成功")
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取数据失败: {e}")
            return None
        except Exception as e:
            logger.error(f"发生未知错误: {e}")
            return None
    
    def parse_telecom_ips(self, html_content):
        """解析HTML并提取电信线路IP"""
        telecom_ips = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.info("开始解析HTML内容")
            
            # 方法1: 查找表格中的IP数据
            tables = soup.find_all('table')
            logger.info(f"找到 {len(tables)} 个表格")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                logger.info(f"表格 {i+1} 有 {len(rows)} 行")
                
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # 查找包含电信关键词的行
                    for text in cell_texts:
                        if any(keyword in text for keyword in self.telecom_keywords):
                            # 在同一行中查找IP地址
                            for cell_text in cell_texts:
                                ip = self.extract_ip(cell_text)
                                if ip and ip not in telecom_ips:
                                    telecom_ips.append(ip)
                                    logger.debug(f"找到电信IP: {ip}")
                            break
            
            # 方法2: 在整个页面中搜索IP模式
            if not telecom_ips:
                logger.info("尝试在整个页面中搜索IP地址")
                all_text = soup.get_text()
                import re
                ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
                all_ips = re.findall(ip_pattern, all_text)
                
                # 简单的IP验证
                for ip in all_ips:
                    if self.is_valid_ip(ip) and ip not in telecom_ips:
                        telecom_ips.append(ip)
            
            # 去重
            telecom_ips = list(set(telecom_ips))
            logger.info(f"共找到 {len(telecom_ips)} 个唯一的电信IP地址")
            
            return telecom_ips
            
        except Exception as e:
            logger.error(f"解析数据失败: {e}")
            return []
    
    def extract_ip(self, text):
        """从文本中提取IP地址"""
        import re
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        match = re.search(ip_pattern, text)
        if match and self.is_valid_ip(match.group()):
            return match.group()
        return None
    
    def is_valid_ip(self, ip):
        """验证IP地址是否有效"""
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                return False
        return True
    
    def save_ips_to_file(self, ips):
        """保存IP地址到文件"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            content = f"""# 电信优选IP地址
# 更新时间: {timestamp}
# 数据来源: {self.target_url}
# 总数: {len(ips)} 个IP地址
# 生成方式: 自动抓取并过滤电信线路

"""
            # 添加每个IP地址
            for ip in sorted(ips):
                content += f"{ip}\n"
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"IP地址已保存到 {self.output_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return False
    
    def run(self):
        """执行完整的更新流程"""
        logger.info("=== 开始电信IP更新任务 ===")
        
        # 获取数据
        html_content = self.fetch_ips_data()
        if not html_content:
            logger.error("无法获取数据，任务终止")
            return False
        
        # 解析电信IP
        telecom_ips = self.parse_telecom_ips(html_content)
        if not telecom_ips:
            logger.warning("未找到电信IP地址")
            # 仍然创建文件，但内容为空或包含说明
            telecom_ips = ["# 本次未找到电信IP地址，请检查数据源或解析逻辑"]
        
        # 保存到文件
        success = self.save_ips_to_file(telecom_ips)
        
        if success:
            logger.info("=== 电信IP更新任务完成 ===")
        else:
            logger.error("=== 电信IP更新任务失败 ===")
        
        return success

def main():
    """主函数"""
    updater = TelecomIPUpdater()
    success = updater.run()
    
    # 设置退出码，用于GitHub Actions
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
