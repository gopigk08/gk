import urllib.request
import urllib.error
import ssl
import sys
import time

# ─── CONFIG ────────────────────────────────────────────────────────────
FRESH_JIO_URL = "https://thanks-to-veer.saqlainhaider8198.workers.dev/jtv90.m3u[srisk]?ua=sktechtv"
OUTPUT_FILE   = "omni-jio.m3u"
RETRY_COUNT   = 3
RETRY_DELAY   = 5

# Fixed header — always written as the first line of omni-jio.m3u.
# Edit the x-tvg-url value here to change EPG sources.
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
    """Removes the existing #EXTM3U header from the downloaded content."""
    lines = content.splitlines()
    filtered_lines = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.upper().startswith("#EXTM3U"):
            continue # Skip the original header
        filtered_lines.append(s)
    return filtered_lines

def main():
    print("=" * 65)
    print("  OMNI JIO M3U Generator — RAW Mode")
    print("=" * 65)

    print(f"\n[1/2] Fetching fresh Jio TV (Raw Data)...")
    jio_content = fetch_url(FRESH_JIO_URL)
    if not jio_content:
        print("❌ Failed to fetch Jio TV. Aborting.")
        sys.exit(1)
        
    jio_lines = process_playlist(jio_content)
    print(f"  ✅ Extracted {len(jio_lines)} lines of raw channel data.")

    print(f"\n[2/2] Writing everything to {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(OUTPUT_HEADER + "\n")
        for line in jio_lines:
            f.write(line + "\n")

    print(f"  ✅ Done!")
    print(f"\n✅ SUCCESS — {OUTPUT_FILE} is ready with ALL raw channels!")
    print("=" * 65)

if __name__ == "__main__":
    main()
