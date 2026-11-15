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

def normalize_name(name):
    n = name.upper()
    for ch in ['-', '—', '－', '–', '_', '.', '·', ' ', '\u3000']:
        n = n.replace(ch, '')
    return n

# 5 个备用地址，脚本只取第一个作为 CCTV17 的主源
CCTV17_URLS = [
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225909/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225907/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221226270/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225908/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225910/1/index.m3u8?fmt=ts2hls",
]

TW_KEYWORDS = [
    "台湾", "中天", "东森", "三立", "TVBS", "民视", "台视", "华视",
    "中视", "公视", "八大", "非凡", "年代", "壹电视", "寰宇",
    "龙华", "靖天", "爱尔达", "MOMO", "客家电视台", "原住民族电视台",
]

def build_cctv17_block():
    """
    只生成 1 条 CCTV17，归入“总台”分组。
    主源用 CCTV17_URLS[0]，其余 4 个留作备用（需要时把索引改成 1~4）。
    """
    return [
        '#EXTINF:-1 group-title="总台",CCTV17',
        '#EXTVLCOPT:network-caching=1000',
        CCTV17_URLS[0],
    ]

def filter_m3u(content):
    lines = content.splitlines()
    output = []
    i = 0
    header_written = False
    cctv17_done = False

    while i < len(lines):
        line = lines[i]

        if line.startswith('#EXTM3U'):
            if not header_written:
                output.append(line)
                header_written = True
            i += 1
            continue

        if line.startswith('#EXTINF'):
            name = line.rsplit(',', 1)[-1].strip()
            norm = normalize_name(name)

            block_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].startswith('#EXTINF') and not lines[i].startswith('#EXTM3U'):
                block_lines.append(lines[i])
                i += 1

            # CCTV-17：丢弃原块，用固定的 1 条“总台 CCTV17”替换
            if 'CCTV17' in norm:
                print(f"🗑️ 识别到原 CCTV-17 条目，丢弃：{name}")
                if not cctv17_done:
                    output.extend(build_cctv17_block())
                    cctv17_done = True
                continue

            # CCTV-4 只留中文
            if 'CCTV4' in norm and '4K' not in norm and '8K' not in norm:
                if '中文' in name:
                    output.extend(block_lines)
                continue

            # 删台湾
            if any(kw in name for kw in TW_KEYWORDS):
                continue

            # 普通 CCTV
            if 'CCTV' in norm:
                if '4K' not in norm and '8K' not in norm:
                    output.extend(block_lines)
                continue

            # 卫视
            if '卫视' in name:
                output.extend(block_lines)
                continue

            # 江西
            if '江西' in name:
                output.extend(block_lines)
                continue

            continue

        i += 1

    # 兜底：源里没有 CCTV-17 时，也保证输出 1 条“总台 CCTV17”
    if not cctv17_done:
        print("ℹ️ 源中未找到原 CCTV-17 条目，主动追加 1 条 CCTV17")
        output.extend(build_cctv17_block())

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
