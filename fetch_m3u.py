import urllib.request
import sys
import os
import re

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

# CCTV17 的 4 条源（第 5 条不要）
CCTV17_URLS = [
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225909/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225907/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221226270/1/index.m3u8?fmt=ts2hls",
    "http://39.135.140.104:6610/PLTV/88888888/224/3221225908/1/index.m3u8?fmt=ts2hls",
]

# 4 条源的显示名，刻意错开，避免播放器按基础名合并
CCTV17_NAMES = ["CCTV17主源", "CCTV17备1", "CCTV17备2", "CCTV17备3"]

# 台标改成与其他频道一致的 suxiaoming 台标库
CCTV17_LOGO = "https://suxiaoming.codeberg.page/iptv/logo/tv/central/CCTV17.png"

TW_KEYWORDS = [
    "台湾", "中天", "东森", "三立", "TVBS", "民视", "台视", "华视",
    "中视", "公视", "八大", "非凡", "年代", "壹电视", "寰宇",
    "龙华", "靖天", "爱尔达", "MOMO", "客家电视台", "原住民族电视台",
    "华藏", "人间卫视",
]

def build_cctv17_block():
    """
    4 条源，名称分别为 CCTV17主源 / 备1 / 备2 / 备3，
    避免播放器按基础名合并；带台标；归入“总台”分组；不写 #EXTVLCOPT。
    """
    block = []
    for name, url in zip(CCTV17_NAMES, CCTV17_URLS):
        block.append(
            f'#EXTINF:-1 tvg-name="{name}" '
            f'tvg-logo="{CCTV17_LOGO}" '
            f'group-title="总台",{name}'
        )
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

        # 文件头
        if line.startswith('#EXTM3U'):
            if not header_written:
                output.append(line)
                header_written = True
            i += 1
            continue

        # 频道块
        if line.startswith('#EXTINF'):
            name = line.rsplit(',', 1)[-1].strip()
            norm = normalize_name(name)

            # 提取 group-title
            gm = re.search(r'group-title="([^"]*)"', line)
            group_title = gm.group(1) if gm else ""

            # 收集整个频道块
            block_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].startswith('#EXTINF') and not lines[i].startswith('#EXTM3U'):
                block_lines.append(lines[i])
                i += 1

            # 规则 1：CCTV-17 → 完全丢弃原块，用 4 条固定的“总台 CCTV17-*”替换（只输出一次）
            if 'CCTV17' in norm:
                print(f"🗑️ 识别到原 CCTV-17 条目，丢弃：{name}")
                if not cctv17_done:
                    output.extend(build_cctv17_block())
                    cctv17_done = True
                continue

            # 规则 2：CCTV-4 只保留“中文”版本（排除 4K/8K）
            if 'CCTV4' in norm and '4K' not in norm and '8K' not in norm:
                if '中文' in name:
                    output.extend(block_lines)
                continue

            # 规则 3：删台湾频道（名称命中关键词，或 group-title 就是“台湾”）
            if any(kw in name for kw in TW_KEYWORDS) or group_title == "台湾":
                print(f"🗑️ 删除台湾频道：{name} (group={group_title})")
                continue

            # 规则 4：普通 CCTV（非 4K/8K）
            if 'CCTV' in norm:
                if '4K' not in norm and '8K' not in norm:
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

    # 兜底：源里没有 CCTV-17 时也保证输出 4 条
    if not cctv17_done:
        print("ℹ️ 源中未找到原 CCTV-17 条目，主动追加 4 条 CCTV17")
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
