import urllib.request
import urllib.error
import ssl
import sys
import time
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────
FRESH_JIO_URL = "https://thanks-to-veer.saqlainhaider8198.workers.dev/jtv90.m3u[srisk]?ua=sktechtv"
OUTPUT_FILE   = "omni-jio.m3u"
RETRY_COUNT   = 3
RETRY_DELAY   = 5

# Fixed header
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

def process_playlist(content):
    lines = content.splitlines()
    filtered_lines = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.upper().startswith("#EXTM3U"):
            continue 
        filtered_lines.append(s)
    return filtered_lines

def main():
    print("=" * 65)
    print("  OMNI JIO M3U Generator — Auto Update Mode")
    print("=" * 65)

    jio_content = fetch_url(FRESH_JIO_URL)
    if not jio_content:
        print("❌ Failed to fetch Jio TV. Aborting.")
        sys.exit(1)
        
    jio_lines = process_playlist(jio_content)
    print(f"  ✅ Extracted {len(jio_lines)} lines of raw channel data.")

    # Get current time
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        # Write EPG Header
        f.write(OUTPUT_HEADER + "\n")
        # 🔥 ఇది యాడ్ చేయడం వల్ల ఫైల్ ప్రతి అరగంటకు 100% ఆటోమేటిక్ గా అప్‌డేట్ అవుతుంది 🔥
        f.write(f"# Last Auto-Updated: {current_time}\n\n")

        for line in jio_lines:
            f.write(line + "\n")

    print(f"  ✅ SUCCESS — {OUTPUT_FILE} is ready and timestamped!")

if __name__ == "__main__":
    main()
