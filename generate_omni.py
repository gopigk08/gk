import urllib.request
import urllib.error
import re
import ssl
import sys
import time
import os
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────
TEMPLATE_FILE = "template.m3u"
FRESH_JIO_URL = "https://thanks-to-veer.saqlainhaider8198.workers.dev/jtv90.m3u[srisk]?ua=sktechtv"
GK_URL        = "https://raw.githubusercontent.com/gopigk08/Omni/main/GK.m3u"
OUTPUT_FILE   = "omni.m3u"
RETRY_COUNT   = 3
RETRY_DELAY   = 5

# Fixed header — always written as the first line of omni.m3u.
OUTPUT_HEADER = '#EXTM3U x-tvg-url="https://raw.githubusercontent.com/mitthu786/tvepg/main/tataplay/epg.xml" x-tvg-url="https://avkb.short.gy/epg.xml.gz"'
# ────────────────────────────────────────────────────────────────────────

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def fetch_url(url, retries=RETRY_COUNT):
    print(f"  Fetching: {url[:90]}...")
    ctx = make_ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": "sktechtv", "Accept": "*/*"})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                data = resp.read().decode("utf-8", errors="replace")
                print(f"  ✅ OK — {len(data):,} bytes")
                return data
        except urllib.error.HTTPError as e:
            print(f"  ⚠️  HTTP {e.code} on attempt {attempt}/{retries}")
        except Exception as e:
            print(f"  ⚠️  Error on attempt {attempt}/{retries}: {e}")
        if attempt < retries:
            time.sleep(RETRY_DELAY)
    print(f"  ❌ All attempts failed.")
    return ""

def is_url_line(line):
    """True if line is a stream URL."""
    s = line.strip()
    return bool(s) and not s.startswith("#") and (s.startswith("http") or s.startswith("rtmp"))

def get_tvg_id(extinf_line):
    """Extract tvg-id from a #EXTINF line."""
    m = re.search(r'tvg-id="([^"]+)"', extinf_line)
    if m and m.group(1).strip():
        return m.group(1).strip()
    parts = extinf_line.split(",")
    if len(parts) > 1:
        return parts[-1].strip()
    return None

def parse_source_into_blocks(content):
    lines = [l.rstrip() for l in content.splitlines()]
    header = "#EXTM3U"
    start_idx = 0
    if lines and re.match(r'#\s*EXTM3U', lines[0].strip(), re.IGNORECASE):
        header = lines[0].strip()
        start_idx = 1

    channels = {}    
    current_block = []
    
    for line in lines[start_idx:]:
        stripped = line.strip()
        if not stripped:
            continue
        
        current_block.append(stripped)
        
        if is_url_line(stripped):
            tvg_id = None
            for bl in current_block:
                if re.match(r'#\s*EXTINF', bl, re.IGNORECASE):
                    tvg_id = get_tvg_id(bl)
                    break
            if tvg_id:
                channels[tvg_id] = current_block[:]
            current_block = []
    
    return header, channels

def parse_template_ids(content):
    header = "#EXTM3U"
    ids = []
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r'#\s*EXTM3U', stripped, re.IGNORECASE):
            header = stripped
        elif re.match(r'#\s*EXTINF', stripped, re.IGNORECASE):
            cid = get_tvg_id(stripped)
            if cid:
                ids.append(cid)
    return header, ids

def parse_gk_blocks(content):
    blocks = []
    current = []
    for line in content.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r'#\s*EXTM3U', s, re.IGNORECASE):
            continue
        current.append(s)
        if is_url_line(s):
            if len(current) >= 2:
                blocks.append(current[:])
            current = []
    return blocks

def main():
    print("=" * 65)
    print("  OMNI M3U Generator — Full Block Mode (Auto-Update)")
    print("=" * 65)

    print(f"\n[1/4] Reading template: {TEMPLATE_FILE}")
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ '{TEMPLATE_FILE}' not found!")
        sys.exit(1)
    with open(TEMPLATE_FILE, "r", encoding="utf-8", errors="replace") as f:
        template_content = f.read()

    tmpl_header, tmpl_ids = parse_template_ids(template_content)
    print(f"  ✅ {len(tmpl_ids)} channel IDs from template")

    print(f"\n[2/4] Fetching fresh Jio TV (with fresh cookies)...")
    jio_content = fetch_url(FRESH_JIO_URL)
    if not jio_content:
        print("❌ Failed to fetch Jio TV. Aborting.")
        sys.exit(1)

    jio_header, jio_channels = parse_source_into_blocks(jio_content)
    print(f"  ✅ {len(jio_channels)} channels parsed (complete blocks)")

    print(f"\n[3/4] Matching {len(tmpl_ids)} template channels...")
    matched = []
    missing = []
    for cid in tmpl_ids:
        if cid in jio_channels:
            matched.append(jio_channels[cid]) 
        else:
            missing.append(cid)

    print(f"  ✅ Matched : {len(matched)}")
    
    print(f"\n[4/4] Fetching GK.m3u...")
    gk_content = fetch_url(GK_URL)
    gk_blocks = parse_gk_blocks(gk_content)
    print(f"  ✅ {len(gk_blocks)} channels from GK.m3u")

    total = len(matched) + len(gk_blocks)
    print(f"\n[5/5] Writing {total} channels → {OUTPUT_FILE}")

    # కరెంట్ టైమ్ ని తీసుకుంటున్నాం
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(OUTPUT_HEADER + "\n")
        
        # 🔥 ఫైల్ ప్రతి అరగంటకు 100% ఆటోమేటిక్ గా అప్‌డేట్ అవ్వడానికి ఈ లైన్ హెల్ప్ అవుతుంది 🔥
        f.write(f"# Last Auto-Updated: {current_time}\n\n")

        for block in matched:
            for line in block:
                f.write(line + "\n")

        for block in gk_blocks:
            for line in block:
                f.write(line + "\n")

    print(f"  ✅ Done!")
    print(f"\n✅ SUCCESS — omni.m3u ready with {total} channels!")
    print("=" * 65)

if __name__ == "__main__":
    main()
