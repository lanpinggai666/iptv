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
    生成 CCTV17 的 5 个源。
    每个源前加 #EXTVLCOPT:network-caching=1000（1秒网络缓冲），
    可减少因网络抖动导致的音画不同步。VLC 系播放器会识别，其他播放器会忽略该标签但不报错。
    频道名带编号（CCTV17-1 ~ CCTV17-5），方便在播放器里逐个测试哪个最流畅。
    """
    block = []
    for idx, url in enumerate(CCTV17_URLS, start=1):
        block.append(f'#EXTINF:-1 group-title="央视",CCTV17-{idx}')
        block.append('#EXTVLCOPT:network-caching=1000')
        block.append(url)
    return block

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

            # CCTV-17 完全替换
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
