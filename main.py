#!/usr/bin/env python3
"""
电信优选IP自动更新程序
使用Selenium模拟浏览器行为，等待页面加载后提取电信IP地址
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        self.driver = None
        
    def setup_webdriver(self):
        """设置Chrome WebDriver"""
        try:
            chrome_options = Options()
            
            # 无头模式
            chrome_options.add_argument('--headless')
            
            # 禁用GPU加速
            chrome_options.add_argument('--disable-gpu')
            
            # 禁用沙箱
            chrome_options.add_argument('--no-sandbox')
            
            # 禁用DevShmUsage
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # 设置用户代理
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 禁用图片加载，加快页面加载速度
            chrome_options.add_argument('--blink-settings=imagesEnabled=false')
            
            # 禁用JavaScript（如果页面不需要JS）
            # chrome_options.add_argument('--disable-javascript')
            
            logger.info("正在启动Chrome WebDriver...")
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 设置页面加载超时时间
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            logger.info("Chrome WebDriver启动成功")
            return True
            
        except Exception as e:
            logger.error(f"WebDriver启动失败: {e}")
            return False
    
    def random_delay(self, min_seconds=3, max_seconds=5):
        """随机延迟"""
        delay = random.uniform(min_seconds, max_seconds)
        logger.info(f"随机延迟 {delay:.2f} 秒...")
        time.sleep(delay)
    
    def wait_for_page_load(self, timeout=30):
        """等待页面加载完成"""
        try:
            logger.info("等待页面加载完成...")
            
            # 等待页面body元素加载
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待页面完全加载
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # 随机延迟3-5秒，模拟用户行为
            self.random_delay(3, 5)
            
            logger.info("页面加载完成")
            return True
            
        except Exception as e:
            logger.error(f"页面加载超时: {e}")
            return False
    
    def fetch_ips_data(self):
        """使用Selenium获取页面数据"""
        try:
            if not self.driver:
                if not self.setup_webdriver():
                    return None
            
            logger.info(f"正在访问: {self.target_url}")
            self.driver.get(self.target_url)
            
            # 等待页面加载
            if not self.wait_for_page_load():
                return None
            
            # 获取页面源码
            page_source = self.driver.page_source
            logger.info(f"页面获取成功，长度: {len(page_source)} 字符")
            
            return page_source
            
        except Exception as e:
            logger.error(f"获取页面数据失败: {e}")
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
            
            # 记录页面结构信息用于调试
            self.debug_page_structure(soup)
            
            # 方法1: 查找所有表格
            tables = soup.find_all('table')
            logger.info(f"找到 {len(tables)} 个表格")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                logger.info(f"表格 {i+1} 有 {len(rows)} 行")
                
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # 调试：记录前几行的内容
                    if j < 3 and cell_texts:
                        logger.debug(f"表格{i+1} 行{j+1} 内容: {cell_texts}")
                    
                    # 检查是否包含电信关键词
                    is_telecom = any(
                        any(keyword.lower() in text.lower() for keyword in self.telecom_keywords)
                        for text in cell_texts
                    )
                    
                    if is_telecom:
                        logger.info(f"在表格{i+1} 行{j+1} 找到电信线路")
                        # 提取IP地址
                        for text in cell_texts:
                            ip = self.extract_ip(text)
                            if ip and ip not in telecom_ips:
                                telecom_ips.append(ip)
                                logger.info(f"找到电信IP: {ip}")
            
            # 方法2: 查找列表项
            list_items = soup.find_all(['li', 'div', 'p'])
            for item in list_items:
                item_text = item.get_text(strip=True)
                if any(keyword.lower() in item_text.lower() for keyword in self.telecom_keywords):
                    ip = self.extract_ip(item_text)
                    if ip and ip not in telecom_ips:
                        telecom_ips.append(ip)
                        logger.info(f"从列表项找到电信IP: {ip}")
            
            # 方法3: 在整个页面中搜索IP
            if len(telecom_ips) < 5:  # 如果找到的IP太少，尝试全文搜索
                logger.info("尝试在整个页面中搜索IP地址")
                all_text = soup.get_text()
                all_ips = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', all_text)
                
                for ip in all_ips:
                    if self.is_valid_ip(ip) and ip not in telecom_ips:
                        telecom_ips.append(ip)
                
                logger.info(f"通过全文搜索找到 {len(all_ips)} 个IP，去重后新增 {len(telecom_ips)} 个")
            
            # 去重和排序
            telecom_ips = sorted(list(set(telecom_ips)))
            logger.info(f"解析完成，共找到 {len(telecom_ips)} 个唯一的电信IP地址")
            
            # 记录前10个IP作为示例
            if telecom_ips:
                logger.info(f"IP示例 (前10个): {telecom_ips[:10]}")
            else:
                logger.warning("未找到任何电信IP地址")
            
            return telecom_ips
            
        except Exception as e:
            logger.error(f"解析数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def debug_page_structure(self, soup):
        """调试页面结构"""
        try:
            # 记录页面标题
            title = soup.find('title')
            if title:
                logger.info(f"页面标题: {title.get_text(strip=True)}")
            
            # 记录所有h1-h6标签
            headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if headers:
                header_texts = [h.get_text(strip=True) for h in headers[:3]]  # 只记录前3个
                logger.info(f"页面标题标签: {header_texts}")
            
            # 记录所有表格的前两行内容用于调试
            tables = soup.find_all('table')
            for i, table in enumerate(tables[:2]):  # 只检查前2个表格
                rows = table.find_all('tr')[:3]  # 只检查前3行
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    if cell_texts:
                        logger.debug(f"表格{i+1} 行{j+1} 样例: {cell_texts}")
                        
        except Exception as e:
            logger.debug(f"调试页面结构时出错: {e}")
    
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
            # 纯IP地址文件 - 每行一个IP
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for ip in ips:
                    f.write(f"{ip}\n")
            
            logger.info(f"IP地址已保存到 {self.output_file}，共 {len(ips)} 个IP")
            
            # JSON文件包含详细信息（可选）
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
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.driver:
                logger.info("正在关闭WebDriver...")
                self.driver.quit()
                logger.info("WebDriver已关闭")
        except Exception as e:
            logger.warning(f"清理资源时出错: {e}")
    
    def run(self):
        """执行完整的更新流程"""
        logger.info("=== 开始电信IP更新任务 ===")
        logger.info(f"当前北京时间: {beijing_timestamp()}")
        
        start_time = beijing_time()
        success = False
        
        try:
            # 获取数据
            html_content = self.fetch_ips_data()
            if not html_content:
                logger.error("无法获取数据，任务终止")
                return False
            
            # 解析电信IP
            telecom_ips = self.parse_telecom_ips(html_content)
            
            # 保存到文件
            success = self.save_ips_to_file(telecom_ips)
            
        except Exception as e:
            logger.error(f"任务执行过程中出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            success = False
        
        finally:
            # 确保清理资源
            self.cleanup()
        
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
    
    updater = TelecomIPUpdater()
    success = updater.run()
    
    # 记录结束信息
    logger.info("程序结束")
    
    # 设置退出码，用于GitHub Actions
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
