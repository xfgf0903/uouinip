import requests
from bs4 import BeautifulSoup

URL = "https://api.uouin.com/cloudflare.html"
OUTPUT_FILE = "china_telecom_ips.txt"

def fetch_telecom_ips():
    res = requests.get(URL, timeout=10)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")

    ips = []
    rows = soup.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            line = cols[0].get_text(strip=True)
            ip = cols[1].get_text(strip=True)
            if line == "电信":
                ips.append(ip)

    # 去重 + 排序
    ips = sorted(set(ips))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(ips))

    print(f"已提取 {len(ips)} 个电信 IP 并保存到 {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_telecom_ips()
