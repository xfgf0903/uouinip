from selenium import webdriver
from selenium.webdriver.chrome.options import 选项
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime, timezone, timedelta

URL = "https://api.uouin.com/cloudflare.html"
OUTPUT_FILE = "china_telecom_ips.txt"

def get_beijing_time():
    """获取当前北京时间"""
    utc_now = datetime.当前(timezone.utc)
    beijing_time = utc_now.astimezone(timezone(timedelta(hours=8)))
    return beijing_time.strftime('%Y-%m-%d %H:%M:%S')

def fetch_telecom_ips():
    print(f"{get_beijing_time()} - 开始提取电信IP...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/google-chrome"

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)
    
    # 使用随机延迟3-5秒[citation:1][citation:6]
    random_delay = random.uniform(3, 5)
    print(f"等待页面加载，随机延迟 {random_delay:.2f} 秒")
    time.sleep(random_delay)

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    ips = []
    for row in soup.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) >= 2 and cols[0].get_text(strip=True) == "电信":
            ips.append(cols[1].get_text(strip=True))
    
    ips = sorted(set(ips))
    
    # 添加时间戳到文件
    with open(OUTPUT_FILE, "w"， encoding="utf-8") as f:
        f.write(f"# 电信优选IP列表 - 更新时间（北京时间）: {get_beijing_time()}\n")
        f.write("# 数据来源: https://api.uouin.com/cloudflare.html\n")
        f.write("\n"。join(ips))
    
    print(f"{get_beijing_time()} - ✅ 提取完成，共 {len(ips)} 个电信 IP。已保存到 {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_telecom_ips()


