import urllib.request
import sys
import os

SOURCE_URL = "https://huangsuming.github.io/iptv/list/tvlist.txt"
OUTPUT_FILE = "output/iptv.m3u"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8").strip()

def is_m3u(text):
    return text.startswith("#EXTM3U") or "#EXTINF" in text

def convert_txt_to_m3u(text):
    lines = ["#EXTM3U"]
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            name, url = line.split(",", 1)
            lines.append(f'#EXTINF:-1,{name.strip()}')
            lines.append(url.strip())
    return "\n".join(lines)

# CCTV-17 的 5 个备用地址（按你提供的顺序）
CCTV17_URLS = [
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225909/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225907/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221226270/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225908/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225910/1/index.m3u8?fmt=ts2hls",
]

# 台湾频道关键词（命中即删除）
TW_KEYWORDS = [
    "台湾", "中天", "东森", "三立", "TVBS", "民视", "台视", "华视",
    "中视", "公视", "八大", "非凡", "年代", "壹电视", "寰宇",
    "龙华", "靖天", "爱尔达", "MOMO", "客家电视台", "原住民族电视台",
]

def filter_m3u(content):
    """
    过滤规则（按优先级）：
    1. CCTV-17 → 替换为你给的 5 个备用地址，名称统一为 CCTV17
    2. CCTV-4 → 只保留名称含“中文”的版本
    3. 台湾频道 → 删除
    4. 普通 CCTV（非 4K/8K）→ 保留
    5. 所有卫视 → 保留
    6. 所有江西频道 → 保留
    7. 其余（非江西地方台等）→ 删除
    """
    lines = content.splitlines()
    output = []
    i = 0
    header_written = False

    while i < len(lines):
        line = lines[i]

        # 文件头
        if line.startswith('#EXTM3U'):
            if not header_written:
                output.append(line)
                header_written = True
            i += 1
            continue

        # 频道块开始
        if line.startswith('#EXTINF'):
            name = line.rsplit(',', 1)[-1].strip()
            upper_name = name.upper()
            # 归一化：去掉横杠和空格，便于匹配 CCTV-17 / CCTV17 / CCTV 17
            normalized = upper_name.replace('-', '').replace(' ', '')
            # 属性部分（保留 tvg-logo、group-title 等）
            attr_part = line.rsplit(',', 1)[0] if ',' in line else line

            # 收集整个频道块（#EXTINF 行 + 后续 URL / #EXTVLCOPT 等行）
            block_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].startswith('#EXTINF') and not lines[i].startswith('#EXTM3U'):
                block_lines.append(lines[i])
                i += 1

            # 规则 1：CCTV-17 替换为 5 个备用地址
            if 'CCTV17' in normalized:
                for url in CCTV17_URLS:
                    output.append(f'{attr_part},CCTV17')
                    output.append(url)
                continue

            # 规则 2：CCTV-4 只保留“中文”版本（先排除 4K/8K）
            if 'CCTV4' in normalized and '4K' not in normalized and '8K' not in normalized:
                if '中文' in name:
                    output.extend(block_lines)
                continue

            # 规则 3：删除台湾频道
            if any(kw in name for kw in TW_KEYWORDS):
                continue

            # 规则 4：普通 CCTV（非 4K/8K）
            if 'CCTV' in upper_name:
                if '4K' not in upper_name and '8K' not in upper_name:
                    output.extend(block_lines)
                continue

            # 规则 5：所有卫视
            if '卫视' in name:
                output.extend(block_lines)
                continue

            # 规则 6：所有江西频道
            if '江西' in name:
                output.extend(block_lines)
                continue

            # 其余删除
            continue

        i += 1

    return '\n'.join(output)

def main():
    try:
        content = fetch(SOURCE_URL)
    except Exception as e:
        print(f"❌ 下载源文件失败: {e}")
        sys.exit(1)

    if is_m3u(content):
        print("✅ 源文件已是 M3U 格式，开始过滤...")
        m3u_content = content
    else:
        print("⚠️ 源文件不是 M3U，先转换为 M3U 格式...")
        m3u_content = convert_txt_to_m3u(content)

    filtered = filter_m3u(m3u_content)
    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(filtered)
    print(f"📄 已写入过滤后的 M3U 文件：{OUTPUT_FILE}")

if __name__ == "__main__":
    main()
