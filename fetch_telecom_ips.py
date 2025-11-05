import re
import requests

URL = "https://api.uouin.com/cloudflare.html"
OUTPUT_FILE = "china_telecom_ips.txt"

def fetch_telecom_ips():
    res = requests.get(URL)
    res.encoding = res.apparent_encoding
    html = res.text

    # 正则匹配：线路为“电信”的 IP
    # 假设每行类似：<td>电信</td><td>1.2.3.4</td>
    pattern = re.compile(r"电信.*?(\d+\.\d+\.\d+\.\d+)")
    ips = pattern.findall(html)

    # 去重 + 排序
    ips = sorted(set(ips))

    # 保存到文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(ips))

    print(f"已提取 {len(ips)} 个电信 IP 并保存到 {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_telecom_ips()
