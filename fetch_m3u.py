import urllib.request
import sys

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

def main():
    try:
        content = fetch(SOURCE_URL)
    except Exception as e:
        print(f"❌ 下载源文件失败: {e}")
        sys.exit(1)

    if is_m3u(content):
        print("✅ 源文件已是 M3U 格式，直接保存。")
        m3u_content = content
    else:
        print("⚠️ 源文件不是 M3U，尝试转换...")
        m3u_content = convert_txt_to_m3u(content)

    import os
    os.makedirs("output", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"📄 已写入 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
