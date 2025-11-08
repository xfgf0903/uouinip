#!/usr/bin/env python3
"""
电信优选IP自动更新程序
使用requests方法提取电信IP地址，避免浏览器依赖问题
"""

import requests
from bs4 import BeautifulSoup
import os
import json
import logging
import sys
import re
import random
import time
from datetime import datetime, timezone, timedelta

# 设置北京时区
BEIJING_TIMEZONE = timezone(timedelta(hours=8))

def beijing_time():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TIMEZONE)

def beijing_timestamp():
    """获取北京时间的字符串表示"""
    return beijing_time().strftime('%Y-%m-%d %H:%M:%S')

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

# 配置日志
log_filename = f"logs/ip_updater_{beijing_time().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename, encoding='utf-8')
    ]
)

# 设置日志时间格式为北京时间
logging.Formatter.converter = lambda *args: beijing_time().timetuple()

logger = logging.getLogger(__name__)

class TelecomIPUpdater:
    def __init__(self):
        self.target_url = "https://api.uouin.com/cloudflare.html"
        self.output_file = "telecom_ips.txt"
        self.telecom_keywords = ['电信', 'China Telecom', 'CT', 'telecom', 'chntel']
        self.current_log_file = log_filename
        
    def random_delay(self, min_seconds=3, max_seconds=5):
        """随机延迟"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"随机延迟 {delay:.2f} 秒...")
        time.sleep(delay)
    
    def fetch_ips_data(self):
        """使用requests获取页面数据"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Referer': 'https://www.google.com/',
                'DNT': '1'
            }
            
            logger.info(f"正在访问: {self.target_url}")
            
            # 随机延迟3-5秒，模拟用户行为
            self.random_delay(3, 5)
            
            # 使用session保持连接
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(self.target_url, timeout=30)
            response.raise_for_status()
            
            # 自动检测编码
            if response.encoding.lower() in ['iso-8859-1', 'windows-1252']:
                response.encoding = response.apparent_encoding or 'utf-8'
                
            logger.info(f"页面获取成功，状态码: {response.status_code}")
            logger.info(f"页面长度: {len(response.text)} 字符")
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取页面数据失败: {e}")
            return None
        except Exception as e:
            logger.error(f"发生未知错误: {e}")
            return None
    
    def parse_telecom_ips(self, html_content):
        """解析HTML并提取电信线路IP"""
        telecom_ips = []
        try:
            if not html_content:
                return []
                
            soup = BeautifulSoup(html_content, 'html.parser')
            logger.info("开始解析HTML内容")
            
            # 移除脚本和样式标签
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 记录页面基本信息
            title = soup.find('title')
            if title:
                logger.info(f"页面标题: {title.get_text(strip=True)}")
            
            # 查找所有文本内容包含电信关键词的元素
            logger.info("搜索包含电信关键词的内容...")
            
            # 方法1: 搜索包含电信关键词的文本
            telecom_texts = soup.find_all(string=lambda text: text and any(
                keyword in text for keyword in self.telecom_keywords
            ))
            
            logger.info(f"找到 {len(telecom_texts)} 处包含电信关键词的文本")
            
            for telecom_text in telecom_texts:
                # 获取父元素的完整文本
                parent = telecom_text.parent
                if parent:
                    parent_text = parent.get_text()
                    # 从文本中提取IP地址
                    ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', parent_text)
                    for ip in ips:
                        if self.is_valid_ip(ip) and ip not in telecom_ips:
                            telecom_ips.append(ip)
                            logger.info(f"从电信相关内容找到IP: {ip}")
            
            # 方法2: 查找表格中的数据
            tables = soup.find_all('table')
            logger.info(f"找到 {len(tables)} 个表格")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    for cell in cells:
                        cell_text = cell.get_text(strip=True)
                        # 检查是否包含电信关键词
                        if any(keyword in cell_text for keyword in self.telecom_keywords):
                            # 从该单元格提取IP
                            ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', cell_text)
                            for ip in ips:
                                if self.is_valid_ip(ip) and ip not in telecom_ips:
                                    telecom_ips.append(ip)
                                    logger.info(f"从表格找到电信IP: {ip}")
            
            # 方法3: 在整个页面中搜索IP（备用方法）
            if len(telecom_ips) < 5:
                logger.info("IP数量较少，尝试全文搜索...")
                all_text = soup.get_text()
                all_ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', all_text)
                
                valid_ips = []
                for ip in all_ips:
                    if self.is_valid_ip(ip) and ip not in telecom_ips:
                        valid_ips.append(ip)
                
                if valid_ips:
                    logger.info(f"全文搜索找到 {len(valid_ips)} 个额外IP")
                    telecom_ips.extend(valid_ips)
            
            # 去重和排序
            telecom_ips = sorted(list(set(telecom_ips)))
            
            logger.info(f"解析完成，共找到 {len(telecom_ips)} 个电信IP地址")
            
            if telecom_ips:
                logger.info(f"IP示例 (前10个): {telecom_ips[:10]}")
            else:
                logger.warning("未找到任何电信IP地址")
                # 记录页面结构用于调试
                self.debug_page_structure(soup)
                
            return telecom_ips
            
        except Exception as e:
            logger.error(f"解析数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def debug_page_structure(self, soup):
        """调试页面结构"""
        try:
            logger.info("=== 页面结构调试信息 ===")
            
            # 记录所有标题
            headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if headers:
                header_texts = [h.get_text(strip=True) for h in headers[:5]]
                logger.info(f"页面标题: {header_texts}")
            
            # 记录所有链接文本
            links = soup.find_all('a')
            link_texts = [link.get_text(strip=True) for link in links if link.get_text(strip=True)]
            unique_links = list(set(link_texts))[:10]  # 只记录前10个唯一的链接文本
            logger.info(f"页面链接示例: {unique_links}")
            
            # 记录页面中所有找到的关键词
            all_text = soup.get_text()
            found_keywords = []
            for keyword in self.telecom_keywords:
                if keyword in all_text:
                    found_keywords.append(keyword)
            
            if found_keywords:
                logger.info(f"页面中包含的关键词: {found_keywords}")
            else:
                logger.info("页面中未找到任何电信关键词")
                
        except Exception as e:
            logger.debug(f"调试页面结构时出错: {e}")
    
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
            # 纯IP地址文件 - 每行一个IP
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for ip in ips:
                    f.write(f"{ip}\n")
            
            logger.info(f"IP地址已保存到 {self.output_file}，共 {len(ips)} 个IP")
            
            # 同时保存JSON格式用于调试
            json_data = {
                "update_time": beijing_timestamp(),
                "timezone": "Asia/Shanghai (UTC+8)",
                "source": self.target_url,
                "total_ips": len(ips),
                "ips": ips
            }
            
            with open('telecom_ips.json', 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info("详细信息已保存到 telecom_ips.json")
            return True
            
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return False
    
    def run(self):
        """执行完整的更新流程"""
        logger.info("=== 开始电信IP更新任务 ===")
        logger.info(f"当前北京时间: {beijing_timestamp()}")
        logger.info(f"目标网址: {self.target_url}")
        
        start_time = beijing_time()
        success = False
        telecom_ips = []
        
        try:
            # 获取数据
            html_content = self.fetch_ips_data()
            if not html_content:
                logger.error("无法获取页面数据，任务终止")
                # 创建空文件表示任务已执行
                self.save_ips_to_file([])
                return False
            
            # 解析电信IP
            telecom_ips = self.parse_telecom_ips(html_content)
            
            # 保存到文件
            success = self.save_ips_to_file(telecom_ips)
            
        except Exception as e:
            logger.error(f"任务执行过程中出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 即使出错也保存空文件
            try:
                self.save_ips_to_file([])
            except:
                pass
            success = False
        
        end_time = beijing_time()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            logger.info(f"=== 电信IP更新任务完成，耗时: {duration:.2f}秒 ===")
            logger.info(f"=== 生成 {len(telecom_ips)} 个电信IP地址 ===")
            logger.info(f"=== 完成时间: {beijing_timestamp()} ===")
        else:
            logger.error(f"=== 电信IP更新任务失败，耗时: {duration:.2f}秒 ===")
        
        return success

def main():
    """主函数"""
    # 记录开始信息
    logger.info("程序启动")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"当前北京时间: {beijing_timestamp()}")
    
    try:
        updater = TelecomIPUpdater()
        success = updater.run()
        
        # 记录结束信息
        logger.info("程序结束")
        
        # 设置退出码，用于GitHub Actions
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
