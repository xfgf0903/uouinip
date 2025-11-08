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
import re
import time

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# 配置日志
log_filename = f"logs/ip_updater_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename, encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class TelecomIPUpdater:
    def __init__(self):
        self.target_url = "https://api.uouin.com/cloudflare.html"
        self.output_file = "telecom_ips.txt"
        self.telecom_keywords = ['电信', 'China Telecom', 'CT', 'telecom', 'chntel']
        self.current_log_file = log_filename
        
    def fetch_ips_data(self):
        """从API获取IP数据"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            logger.info(f"开始从 {self.target_url} 获取数据")
            response = requests.get(self.target_url, headers=headers, timeout=45)
            response.raise_for_status()
            
            # 自动检测编码
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                response.encoding = response.apparent_encoding or 'utf-8'
                
            logger.info(f"数据获取成功，长度: {len(response.text)} 字符")
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
            
            # 移除脚本和样式标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 方法1: 查找所有表格
            tables = soup.find_all('table')
            logger.info(f"找到 {len(tables)} 个表格")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                logger.info(f"表格 {i+1} 有 {len(rows)} 行")
                
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # 检查是否包含电信关键词
                    is_telecom = any(
                        any(keyword in text for keyword in self.telecom_keywords)
                        for text in cell_texts
                    )
                    
                    if is_telecom:
                        # 提取IP地址
                        for text in cell_texts:
                            ip = self.extract_ip(text)
                            if ip and ip not in telecom_ips:
                                telecom_ips.append(ip)
                                logger.info(f"找到电信IP: {ip}")
            
            # 方法2: 在整个页面中搜索IP
            if len(telecom_ips) < 3:  # 如果找到的IP太少，尝试全文搜索
                logger.info("尝试在整个页面中搜索IP地址")
                all_text = soup.get_text()
                all_ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', all_text)
                
                for ip in all_ips:
                    if self.is_valid_ip(ip) and ip not in telecom_ips:
                        telecom_ips.append(ip)
                
                logger.info(f"通过全文搜索找到 {len(all_ips)} 个IP，去重后新增 {len(telecom_ips) - len(all_ips)} 个")
            
            # 方法3: 查找包含IP的pre或code标签
            pre_tags = soup.find_all(['pre', 'code'])
            for pre in pre_tags:
                pre_text = pre.get_text()
                if any(keyword in pre_text for keyword in self.telecom_keywords):
                    ips_in_pre = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', pre_text)
                    for ip in ips_in_pre:
                        if self.is_valid_ip(ip) and ip not in telecom_ips:
                            telecom_ips.append(ip)
                            logger.info(f"从pre/code标签找到电信IP: {ip}")
            
            # 去重和排序
            telecom_ips = sorted(list(set(telecom_ips)))
            logger.info(f"解析完成，共找到 {len(telecom_ips)} 个唯一的电信IP地址")
            
            # 记录前5个IP作为示例
            if telecom_ips:
                logger.info(f"IP示例: {telecom_ips[:5]}")
            
            return telecom_ips
            
        except Exception as e:
            logger.error(f"解析数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def extract_ip(self, text):
        """从文本中提取IP地址"""
        match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
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
        # 排除一些常见的无效IP
        if ip.startswith('0.') or ip.startswith('127.') or ip.startswith('169.254.'):
            return False
        if ip == '255.255.255.255':
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
            for ip in ips:
                content += f"{ip}\n"
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"IP地址已保存到 {self.output_file}")
            
            # 同时保存JSON格式用于其他用途
            json_data = {
                "update_time": timestamp,
                "source": self.target_url,
                "total_ips": len(ips),
                "ips": ips
            }
            
            with open('telecom_ips.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info("JSON格式数据已保存到 telecom_ips.json")
            return True
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return False
    
    def create_symlink_to_latest_log(self):
        """创建指向最新日志文件的符号链接"""
        try:
            if os.path.exists('latest_log.txt'):
                os.remove('latest_log.txt')
            os.symlink(self.current_log_file, 'latest_log.txt')
            logger.info(f"创建日志符号链接: latest_log.txt -> {self.current_log_file}")
        except Exception as e:
            logger.warning(f"创建日志符号链接失败: {e}")
    
    def run(self):
        """执行完整的更新流程"""
        logger.info("=== 开始电信IP更新任务 ===")
        
        start_time = datetime.now()
        
        # 获取数据
        html_content = self.fetch_ips_data()
        if not html_content:
            logger.error("无法获取数据，任务终止")
            # 即使失败也创建日志文件
            self.create_symlink_to_latest_log()
            return False
        
        # 解析电信IP
        telecom_ips = self.parse_telecom_ips(html_content)
        
        # 保存到文件
        success = self.save_ips_to_file(telecom_ips)
        
        # 创建日志符号链接
        self.create_symlink_to_latest_log()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            logger.info(f"=== 电信IP更新任务完成，耗时: {duration:.2f}秒 ===")
        else:
            logger.error(f"=== 电信IP更新任务失败，耗时: {duration:.2f}秒 ===")
        
        return success

def main():
    """主函数"""
    # 记录开始信息
    logger.info("程序启动")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    
    updater = TelecomIPUpdater()
    success = updater.run()
    
    # 记录结束信息
    logger.info("程序结束")
    
    # 设置退出码，用于GitHub Actions
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
