import re
import sys
import requests
from pathlib import Path

URL = "https://api.uouin.com/cloudflare.html"  # 数据源
OUTPUT_PATH = Path("data/telecom_ips.txt")     # 输出到仓库目录
ENCODING = "utf-8"

# IPv4 提取正则（提取）与校验
IPV4_EXTRACT = re.compile(r'(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.(?:25[0-5]|2[0-4]\d|1?\d{1,2})')
def is_valid_ipv4(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4: return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False

def get_html(url: str, timeout: int = 20) -> str:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    # 页面一般为 UTF-8
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

def extract_telecom_ips(html: str):
    # 简单按行拆分，筛选包含“电信”的行，再从该行提取 IPv4
    ips = []
    for line in html.splitlines():
        if "电信" in line:
            for ip in IPV4_EXTRACT.findall(line):
                if is_valid_ipv4(ip):
                    ips.append(ip)
    # 去重且保序
    seen = set()
    ordered = []
    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            ordered.append(ip)
    return ordered

def main():
    try:
        html = get_html(URL, timeout=20)
    except Exception as e:
        print(f"Error fetch: {e}", file=sys.stderr)
        sys.exit(2)

    ips = extract_telecom_ips(html)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding=ENCODING) as f:
        f.write(",".join(ips))

if __name__ == "__main__":
    main()
