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
    """兜底转换：如果源不再是 M3U，尝试将每行 名称,链接 转为 M3U 格式"""
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

def filter_m3u(content):
    """按规则过滤 M3U 频道：
       保留 CCTV（不含4K/8K）、所有卫视、所有江西频道。
       其余（非江西的地方市/县台）删除。
    """
    lines = content.splitlines()
    output = []
    i = 0
    header_written = False

    while i < len(lines):
        line = lines[i]

        # 处理文件头
        if line.startswith('#EXTM3U'):
            if not header_written:
                output.append(line)
                header_written = True
            i += 1
            continue

        # 处理频道块
        if line.startswith('#EXTINF'):
            # 提取频道名：最后一个逗号后的内容
            name = line.rsplit(',', 1)[-1].strip()
            upper_name = name.upper()

            keep = False
            # 规则1：CCTV 频道，但排除 4K / 8K
            if 'CCTV' in upper_name:
                if '4K' not in upper_name and '8K' not in upper_name:
                    keep = True
            # 规则2：所有卫视
            elif '卫视' in name:
                keep = True
            # 规则3：所有江西频道
            elif '江西' in name:
                keep = True

            if keep:
                # 输出当前 #EXTINF 行
                output.append(line)
                i += 1
                # 输出后续非 #EXTINF / #EXTM3U 的行（通常是 URL 或 #EXTVLCOPT 等）
                while i < len(lines) and not lines[i].startswith('#EXTINF') and not lines[i].startswith('#EXTM3U'):
                    output.append(lines[i])
                    i += 1
            else:
                # 跳过整个频道块
                i += 1
                while i < len(lines) and not lines[i].startswith('#EXTINF') and not lines[i].startswith('#EXTM3U'):
                    i += 1
            continue

        # 其他行（如空行）直接跳过
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
